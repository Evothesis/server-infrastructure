from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks, Path
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import json
import logging
import os
import threading
import time
import httpx
from ipaddress import ip_address, AddressValueError
from typing import Optional, List, Dict, Any, Tuple

from .database import engine, get_db, DATABASE_URL
from .models import Base, EventLog
from .s3_export import create_raw_data_exporter
from .rate_limiter import RateLimitMiddleware
from .cors_middleware import DynamicCORSMiddleware
from .validation_schemas import CollectionRequest
from .validation_middleware import RequestValidationMiddleware
from .error_handler import custom_general_exception_handler

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection established (credentials not logged for security)
logger.info("Database connection established")

# Create tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to create database tables: {e}")
    raise

# Set pixel management endpoint 
PIXEL_MANAGEMENT_URL = os.getenv("PIXEL_MANAGEMENT_URL", "https://pixel-management-275731808857.us-central1.run.app")

async def get_client_id_for_domain(domain: str) -> str:
    """Get client_id for a domain from pixel-management"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{PIXEL_MANAGEMENT_URL}/api/v1/config/domain/{domain}")
            if response.status_code == 200:
                config = response.json()
                return config.get("client_id", f"unknown_{domain}")
            else:
                logger.warning(f"Domain {domain} not authorized: HTTP {response.status_code}")
                return f"unauthorized_{domain}"
    except Exception as e:
        logger.error(f"Failed to get client config for domain {domain}: {e}")
        return f"error_{domain}"

app = FastAPI(title="Analytics API", version="1.0.0")

# Add security middleware in correct order
app.add_middleware(DynamicCORSMiddleware, pixel_management_url=PIXEL_MANAGEMENT_URL)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(RateLimitMiddleware)

# Add exception handlers for secure error responses
app.add_exception_handler(Exception, custom_general_exception_handler)

# ============================================================================
# Configuration Cache (Thread-safe in-memory caching)
# ============================================================================

class ConfigCache:
    def __init__(self, ttl_seconds: int = 300):  # 5 minute TTL
        self.cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if key not in self.cache:
                return None
                
            data, timestamp = self.cache[key]
            if time.time() - timestamp > self.ttl_seconds:
                # Cache expired - remove atomically
                del self.cache[key]
                return None
                
            return data
    
    def set(self, key: str, data: Dict[str, Any]):
        with self._lock:
            self.cache[key] = (data, time.time())
    
    def clear(self):
        with self._lock:
            self.cache.clear()

# Global cache instance
config_cache = ConfigCache(ttl_seconds=300)  # 5 minute cache

# ============================================================================
# Pixel Management Service Integration
# ============================================================================

async def get_client_config(client_id: str) -> Dict[str, Any]:
    """Fetch client configuration from pixel management service with caching"""
    
    # Check cache first
    cached_config = config_cache.get(client_id)
    if cached_config:
        logger.info(f"Using cached config for client {client_id}")
        return cached_config
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PIXEL_MANAGEMENT_URL}/api/v1/config/client/{client_id}",
                timeout=5.0
            )
            
            if response.status_code == 404:
                logger.warning(f"Client {client_id} not found")
                raise HTTPException(status_code=404, detail="Client not found or inactive")
            
            if response.status_code != 200:
                logger.error(f"Config service error for client {client_id}: {response.status_code}")
                raise HTTPException(status_code=502, detail="Configuration service unavailable")
            
            config = response.json()
            
            # Cache the config
            config_cache.set(client_id, config)
            logger.info(f"Fetched and cached config for client {client_id}")
            
            return config
            
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to pixel management service: {e}")
        raise HTTPException(status_code=502, detail="Configuration service unavailable")

# ============================================================================
# Utility Functions
# ============================================================================

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

def redact_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove or redact potentially sensitive information"""
    if not isinstance(data, dict):
        return data
    
    sensitive_patterns = [
        'password', 'pwd', 'pass', 'secret', 'token', 'key',
        'email', 'mail', 'phone', 'tel', 'ssn', 'social',
        'credit', 'card', 'cvv', 'cvc', 'billing'
    ]
    
    redacted = {}
    for key, value in data.items():
        key_lower = str(key).lower()
        
        # Check if key contains sensitive pattern
        is_sensitive = any(pattern in key_lower for pattern in sensitive_patterns)
        
        if is_sensitive:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_sensitive_data(value)
        elif isinstance(value, str) and len(value) > 100:
            # Truncate very long strings that might contain sensitive data
            redacted[key] = value[:100] + "..."
        else:
            redacted[key] = value
    
    return redacted

def create_event_record(event_data: Dict[str, Any], client_ip: str, user_agent: str, event_timestamp: datetime, client_id: str) -> Dict[str, Any]:
    """Create a standardized event record for database insertion"""
    
    # Redact sensitive data from nested eventData
    safe_event_data = redact_sensitive_data(event_data.get("eventData", {}))
    
    # Create a clean copy of the complete event data for raw_event_data
    raw_event_data = event_data.copy()
    if "eventData" in raw_event_data:
        raw_event_data["eventData"] = safe_event_data
    
    return {
        "event_type": event_data.get("eventType", "unknown"),
        "session_id": event_data.get("sessionId"),
        "visitor_id": event_data.get("visitorId"),
        "site_id": event_data.get("siteId", "unknown"),
        "timestamp": event_timestamp,
        "url": event_data.get("url"),
        "path": event_data.get("path"),
        "user_agent": user_agent,
        "ip_address": client_ip,
        "raw_event_data": raw_event_data,
        "client_id": client_id,
        "created_at": datetime.utcnow()
    }

def process_batch_events(batch_data: Dict[str, Any], client_ip: str, user_agent: str, client_id: str) -> List[Dict[str, Any]]:
    """Process batch events and return list of events ready for insertion"""
    individual_events = batch_data.get("events", [])
    events_to_insert = []
    
    # Process the batch wrapper as an event
    batch_timestamp = parse_timestamp(batch_data.get("timestamp", ""))
    batch_event_record = create_event_record(batch_data, client_ip, user_agent, batch_timestamp, client_id)
    events_to_insert.append(batch_event_record)
    
    logger.info(f"Processing batch with {len(individual_events)} individual events for client {client_id}")
    
    # Process each event in the batch
    for individual_event in individual_events:
        event_timestamp = parse_timestamp(individual_event.get("timestamp", batch_data.get("timestamp", "")))
        
        # Create complete event data by merging batch context with individual event
        complete_event_data = {
            "eventType": individual_event.get("eventType", "unknown"),
            "sessionId": batch_data.get("sessionId"),
            "visitorId": batch_data.get("visitorId"),
            "siteId": batch_data.get("siteId"),
            "timestamp": individual_event.get("timestamp", batch_data.get("timestamp")),
            "referrer": batch_data.get("referrer"),
            "url": batch_data.get("url"),
            "path": batch_data.get("path"),
            "eventData": individual_event.get("eventData", {}),
            # Include any additional context from batch
            "attribution": batch_data.get("attribution"),
            "browser": batch_data.get("browser"),
            "page": batch_data.get("page")
        }
        
        event_record = create_event_record(complete_event_data, client_ip, user_agent, event_timestamp, client_id)
        events_to_insert.append(event_record)
    
    return events_to_insert

# ============================================================================
# API Endpoints
# ============================================================================

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
async def collect_events(
    request_data: CollectionRequest,
    request: Request, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """
    Collect analytics events with comprehensive security validation
    
    Features:
    - Input validation with size limits (1MB request, 100 events/batch)
    - Domain authorization via pixel-management
    - Client attribution for multi-tenant tracking
    - Bulk insert optimization for performance
    - Secure error handling
    """
    try:
        # Extract client information
        client_ip = extract_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Get requesting domain and validate authorization
        requesting_domain = request.headers.get("host", "").split(":")[0]
        client_id = await get_client_id_for_domain(requesting_domain)
        
        # Convert validated Pydantic model to dict for processing
        event_data = request_data.dict()
        
        # Determine if this is a batch or single event
        batch_size = 1
        if event_data.get("eventType") == "batch" and event_data.get("events"):
            batch_size = len(event_data["events"]) + 1  # +1 for wrapper event
        
        # Process events
        events_to_insert = []
        
        if event_data.get("eventType") == "batch" and event_data.get("events"):
            events_to_insert = process_batch_events(event_data, client_ip, user_agent, client_id)
        else:
            event_timestamp = parse_timestamp(event_data.get("timestamp", ""))
            event_record = create_event_record(event_data, client_ip, user_agent, event_timestamp, client_id)
            events_to_insert.append(event_record)
        
        # Bulk insert with transaction
        try:
            if events_to_insert:
                db.bulk_insert_mappings(EventLog, events_to_insert)
                db.commit()
                logger.info(f"Bulk inserted {len(events_to_insert)} events for client {client_id}")
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            db.rollback()
            return {"status": "accepted", "message": "Processing queued"}
        
        return {
            "status": "success", 
            "events_processed": len(events_to_insert),
            "client_id": client_id,
            "batch_size": batch_size
        }
        
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Pixel management service error: {e}")
        raise HTTPException(status_code=502, detail="Configuration service unavailable")
    except Exception as e:
        logger.error(f"Collection processing error: {e}")
        raise HTTPException(status_code=500, detail="Collection service error")

@app.get("/events/count")
async def get_event_count(db: Session = Depends(get_db)):
    """Get total event count"""
    try:
        result = db.execute(text("SELECT COUNT(*) FROM events_log"))
        count = result.scalar()
        return {"total_events": count, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Failed to get event count: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")

@app.get("/events/recent")
async def get_recent_events(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent events for debugging"""
    try:
        result = db.execute(
            text("SELECT event_type, site_id, created_at, session_id FROM events_log ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit}
        )
        events = []
        for row in result:
            events.append({
                "event_type": row[0],
                "site_id": row[1], 
                "created_at": row[2].isoformat() if row[2] else None,
                "session_id": row[3]
            })
        return {"recent_events": events, "count": len(events)}
    except Exception as e:
        logger.error(f"Failed to get recent events: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")


# ============================================================================
# S3 Export Endpoints (existing functionality)
# ============================================================================

# Initialize S3 exporter
raw_data_exporter = create_raw_data_exporter()

@app.post("/export/run")
async def trigger_export(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger manual raw S3 export"""
    try:
        # Run raw export in background
        background_tasks.add_task(raw_data_exporter.export_raw_events, db)
        return {"message": "Raw export started", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Failed to start raw export: {e}")
        raise HTTPException(status_code=500, detail="Raw export failed to start")

@app.get("/export/status")
async def get_export_status(db: Session = Depends(get_db)):
    """Get raw export status"""
    try:
        status = raw_data_exporter.get_export_status(db)
        return status
    except Exception as e:
        logger.error(f"Failed to get export status: {e}")
        raise HTTPException(status_code=500, detail="Status check failed")

@app.get("/export/config")
async def get_export_config():
    """Get export configuration"""
    try:
        config = s3_exporter.get_config()
        return config
    except Exception as e:
        logger.error(f"Failed to get export config: {e}")
        raise HTTPException(status_code=500, detail="Config check failed")