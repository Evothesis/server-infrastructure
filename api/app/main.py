from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import json
import logging
import os
from ipaddress import ip_address, AddressValueError
from typing import Optional, List, Dict, Any

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

def create_event_record(event_data: Dict[str, Any], client_ip: str, user_agent: str, 
                       event_timestamp: datetime) -> Dict[str, Any]:
    """Create a database record dictionary from event data"""
    return {
        'event_type': event_data.get("eventType", "unknown"),
        'session_id': event_data.get("sessionId"),
        'visitor_id': event_data.get("visitorId"),
        'site_id': event_data.get("siteId"),
        'timestamp': event_timestamp,
        'url': event_data.get("url"),
        'path': event_data.get("path"),
        'user_agent': user_agent,
        'ip_address': client_ip,
        'raw_event_data': event_data
    }

def process_batch_events(batch_data: Dict[str, Any], client_ip: str, user_agent: str) -> List[Dict[str, Any]]:
    """Process batch event data and return list of event records"""
    events_to_insert = []
    
    # Parse batch timestamp
    batch_timestamp_str = batch_data.get("timestamp")
    if batch_timestamp_str:
        batch_timestamp = parse_timestamp(batch_timestamp_str)
    else:
        batch_timestamp = datetime.utcnow()
    
    # Add the batch event itself
    batch_record = create_event_record(batch_data, client_ip, user_agent, batch_timestamp)
    events_to_insert.append(batch_record)
    
    # Process individual events within the batch
    batch_events = batch_data.get("events", [])
    for individual_event in batch_events:
        # Parse individual event timestamp
        event_timestamp_str = individual_event.get("timestamp")
        if event_timestamp_str:
            event_timestamp = parse_timestamp(event_timestamp_str)
        else:
            event_timestamp = batch_timestamp
        
        # Create complete event data by merging batch context with individual event
        complete_event_data = {
            "eventType": individual_event.get("eventType", "unknown"),
            "sessionId": batch_data.get("sessionId"),
            "visitorId": batch_data.get("visitorId"),
            "siteId": batch_data.get("siteId"),
            "timestamp": individual_event.get("timestamp", batch_data.get("timestamp")),
            "url": batch_data.get("url"),
            "path": batch_data.get("path"),
            "eventData": individual_event.get("eventData", {}),
            # Include any additional context from batch
            "attribution": batch_data.get("attribution"),
            "browser": batch_data.get("browser"),
            "page": batch_data.get("page")
        }
        
        event_record = create_event_record(complete_event_data, client_ip, user_agent, event_timestamp)
        events_to_insert.append(event_record)
    
    return events_to_insert

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
        
        events_to_insert = []
        event_count = 0
        
        # Check if this is a batch event
        if event_data.get("eventType") == "batch":
            # Process batch events
            events_to_insert = process_batch_events(event_data, client_ip, user_agent)
            event_count = len(events_to_insert)
            logger.info(f"Processing batch with {len(event_data.get('events', []))} individual events")
        else:
            # Process single event
            event_timestamp_str = event_data.get("timestamp")
            if event_timestamp_str:
                event_timestamp = parse_timestamp(event_timestamp_str)
            else:
                event_timestamp = datetime.utcnow()
            
            event_record = create_event_record(event_data, client_ip, user_agent, event_timestamp)
            events_to_insert = [event_record]
            event_count = 1
        
        # Bulk insert all events
        if events_to_insert:
            try:
                # Use bulk_insert_mappings for optimal performance
                db.bulk_insert_mappings(EventLog, events_to_insert)
                db.commit()
                
                # Log the successful save
                site_id = events_to_insert[0].get('site_id', 'unknown')
                logger.info(f"Bulk inserted {event_count} events from {site_id}")
                
            except Exception as db_error:
                logger.error(f"Database bulk insert failed: {str(db_error)}")
                db.rollback()
                # Still return success to client to avoid blocking tracking
                return {
                    "status": "error",
                    "message": "Event processing failed",
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return {
            "status": "success",
            "message": f"{event_count} event(s) received and stored",
            "events_processed": event_count,
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