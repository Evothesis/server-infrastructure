from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import json
import logging
import os
from ipaddress import ip_address, AddressValueError
from typing import Optional

from .database import engine, get_db, DATABASE_URL
from .models import Base, EventLog
from .s3_export import create_s3_exporter

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
        # Test database connection
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
                    "created_at": event.created_at.isoformat(),
                    "processed_at": event.processed_at.isoformat() if event.processed_at else None
                }
                for event in events
            ]
        }
    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
        raise HTTPException(status_code=500, detail="Database error")

# S3 Export Endpoints

@app.post("/export/run")
async def run_export(
    background_tasks: BackgroundTasks,
    since: Optional[str] = None,
    limit: int = 10000,
    db: Session = Depends(get_db)
):
    """Trigger manual S3 export"""
    try:
        # Parse since parameter if provided
        since_datetime = None
        if since:
            try:
                since_datetime = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid datetime format for 'since' parameter")
        
        # Create S3 exporter
        exporter = create_s3_exporter()
        
        # Run export synchronously for now (can be moved to background for large exports)
        result = exporter.export_events(db, since_datetime, limit)
        
        return result
        
    except ValueError as e:
        logger.error(f"S3 export configuration error: {e}")
        raise HTTPException(status_code=500, detail=f"Export configuration error: {str(e)}")
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/export/status")
async def get_export_status(db: Session = Depends(get_db)):
    """Get S3 export pipeline status"""
    try:
        exporter = create_s3_exporter()
        status = exporter.get_export_status(db)
        return status
    except ValueError as e:
        logger.error(f"S3 export configuration error: {e}")
        raise HTTPException(status_code=500, detail=f"Export configuration error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get export status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@app.get("/export/config")
async def get_export_config():
    """Get current export configuration"""
    try:
        from .s3_export import S3ExportConfig
        config = S3ExportConfig()
        
        # Return safe configuration info (no secrets)
        return {
            "client_bucket": config.client_bucket,
            "client_region": config.client_region,
            "backup_bucket": config.backup_bucket,
            "backup_region": config.backup_region,
            "export_format": config.export_format,
            "export_schedule": config.export_schedule,
            "site_id": config.site_id,
            "credentials_configured": {
                "client": bool(config.client_access_key and config.client_secret_key),
                "backup": bool(config.backup_access_key and config.backup_secret_key)
            }
        }
    except ValueError as e:
        logger.error(f"S3 export configuration error: {e}")
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get export config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get configuration")