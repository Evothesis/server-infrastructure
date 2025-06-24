from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text  # Add this import
from datetime import datetime
import json
import logging
import os
from ipaddress import ip_address, AddressValueError

from .database import engine, get_db, DATABASE_URL
from .models import Base, EventLog
from .etl import router as etl_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug: Print database connection info
logger.info(f"DATABASE_URL from env: {os.getenv('DATABASE_URL', 'NOT SET')}")
logger.info(f"Actual DATABASE_URL being used: {DATABASE_URL}")

# Create tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to create database tables: {e}")
    raise

app = FastAPI(title="Analytics API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include ETL router
app.include_router(etl_router)

def extract_client_ip(request: Request) -> str:
    """Extract client IP address from request headers"""
    # Check common headers for real IP (in case of proxy/load balancer)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        client_ip = forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.client.host
    
    # Validate IP address
    try:
        ip_address(client_ip)
        return client_ip
    except (AddressValueError, TypeError):
        return "127.0.0.1"  # Fallback for invalid IPs

def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO timestamp string to datetime object"""
    try:
        # Handle ISO format with Z suffix
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        return datetime.utcnow()

@app.get("/")
async def root():
    return {"message": "Analytics API is running", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health")
async def health(db: Session = Depends(get_db)):
    """Health check with database connectivity test"""
    try:
        # Test database connection - FIXED: Added text() wrapper
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")

@app.post("/collect")
async def collect_event(request: Request, db: Session = Depends(get_db)):
    """Collect analytics events from the tracking pixel"""
    try:
        # Get the raw body
        body = await request.body()
        
        # Get client IP and user agent
        client_ip = extract_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Parse JSON if present
        if body:
            try:
                event_data = json.loads(body)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON")
        else:
            # Handle GET request with query parameters
            event_data = dict(request.query_params)
        
        # Extract core fields for database columns
        event_type = event_data.get("eventType", "unknown")
        session_id = event_data.get("sessionId")
        visitor_id = event_data.get("visitorId")
        site_id = event_data.get("siteId")
        url = event_data.get("url")
        path = event_data.get("path")
        
        # Parse timestamp
        timestamp_str = event_data.get("timestamp")
        if timestamp_str:
            event_timestamp = parse_timestamp(timestamp_str)
        else:
            event_timestamp = datetime.utcnow()
        
        # Create database record
        event_record = EventLog(
            event_type=event_type,
            session_id=session_id,
            visitor_id=visitor_id,
            site_id=site_id,
            timestamp=event_timestamp,
            url=url,
            path=path,
            user_agent=user_agent,
            ip_address=client_ip,
            raw_event_data=event_data
        )
        
        # Save to database
        db.add(event_record)
        db.commit()
        db.refresh(event_record)
        
        # Log the successful save
        logger.info(f"Event saved: {event_type} from {site_id} (ID: {event_record.id})")
        
        return {
            "status": "success",
            "message": "Event received and stored",
            "event_id": str(event_record.event_id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        # Still return success to client, but log the error
        return {
            "status": "error",
            "message": "Event processing failed",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.options("/collect")
async def collect_options():
    """Handle CORS preflight requests"""
    return {"status": "ok"}

@app.get("/events/count")
async def get_events_count(db: Session = Depends(get_db)):
    """Get total count of events in database"""
    try:
        count = db.query(EventLog).count()
        return {"total_events": count}
    except Exception as e:
        logger.error(f"Error getting events count: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/events/recent")
async def get_recent_events(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent events for debugging"""
    try:
        events = db.query(EventLog).order_by(EventLog.created_at.desc()).limit(limit).all()
        return {
            "events": [
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "session_id": event.session_id,
                    "site_id": event.site_id,
                    "timestamp": event.timestamp.isoformat(),
                    "created_at": event.created_at.isoformat()
                }
                for event in events
            ]
        }
    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
        raise HTTPException(status_code=500, detail="Database error")