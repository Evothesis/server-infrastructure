from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import json
import logging
import os
import time
import httpx
from ipaddress import ip_address, AddressValueError
from typing import Optional, List, Dict, Any, Tuple

from .database import engine, get_db, DATABASE_URL
from .models import Base, EventLog
from .s3_export import create_s3_exporter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug: Print database connection info
logger.info(f"DATABASE_URL from env: {os.getenv('DATABASE_URL', 'NOT SET')}")
logger.info(f"Actual DATABASE_URL being used: {DATABASE_URL}")

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

# ============================================================================
# Configuration Cache (Simple in-memory caching for MVP)
# ============================================================================

class ConfigCache:
    def __init__(self, ttl_seconds: int = 300):  # 5 minute TTL
        self.cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key not in self.cache:
            return None
            
        data, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            # Cache expired
            del self.cache[key]
            return None
            
        return data
    
    def set(self, key: str, data: Dict[str, Any]):
        self.cache[key] = (data, time.time())
    
    def clear(self):
        self.cache.clear()

# Global cache instance
config_cache = ConfigCache(ttl_seconds=300)  # 5 minute cache

# ============================================================================
# Pixel Management Service Integration
# ============================================================================

PIXEL_MANAGEMENT_URL = os.getenv("PIXEL_MANAGEMENT_URL", "http://pixel-management:8000")

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
# Pixel Template System
# ============================================================================

def get_base_tracking_code() -> str:
    """Base tracking pixel JavaScript template"""
    return """
(function() {
    // Evothesis Analytics Pixel - Dynamically Generated
    // Configuration injected from server
    const config = {CONFIG_PLACEHOLDER};
    
    // Privacy compliance check
    if (config.consent && config.consent.required && !hasUserConsent()) {
        console.log('[Evothesis] Consent required - tracking blocked');
        return;
    }
    
    // Respect Do Not Track
    if (navigator.doNotTrack === '1' || window.doNotTrack === '1') {
        console.log('[Evothesis] Do Not Track enabled - respecting user preference');
        return;
    }
    
    // Core tracking configuration
    var trackingConfig = {
        apiEndpoint: config.apiEndpoint || '/collect',
        sessionTimeout: 30 * 60 * 1000, // 30 minutes
        batchTimeout: 60 * 1000, // 1 minute inactivity
        maxBatchSize: 50,
        privacyLevel: config.privacy_level || 'standard'
    };
    
    // Session management
    var sessionManager = {
        getSessionId: function() {
            var currentTime = Date.now();
            var sessionId = localStorage.getItem('_evothesis_session_id');
            var lastActivity = parseInt(localStorage.getItem('_evothesis_last_activity') || '0');
            
            // Check session timeout
            var sessionExpired = (currentTime - lastActivity) > trackingConfig.sessionTimeout;
            
            if (!sessionId || sessionExpired) {
                sessionId = 'sess_' + Math.random().toString(36).substring(2, 15) + 
                           Math.random().toString(36).substring(2, 15);
                localStorage.setItem('_evothesis_session_id', sessionId);
                localStorage.setItem('_evothesis_session_start', currentTime.toString());
            }
            
            localStorage.setItem('_evothesis_last_activity', currentTime.toString());
            return sessionId;
        },
        
        getVisitorId: function() {
            var visitorId = localStorage.getItem('_evothesis_visitor_id');
            if (!visitorId) {
                visitorId = 'vis_' + Math.random().toString(36).substring(2, 15) + 
                           Math.random().toString(36).substring(2, 15);
                localStorage.setItem('_evothesis_visitor_id', visitorId);
            }
            return visitorId;
        }
    };
    
    // Event batching system
    var eventBatcher = {
        batch: [],
        batchTimer: null,
        
        addEvent: function(eventType, eventData) {
            var event = {
                eventType: eventType,
                eventData: eventData || {},
                timestamp: new Date().toISOString()
            };
            
            this.batch.push(event);
            
            // Send immediately if batch is full
            if (this.batch.length >= trackingConfig.maxBatchSize) {
                this.sendBatch();
                return;
            }
            
            // Reset timer
            if (this.batchTimer) {
                clearTimeout(this.batchTimer);
            }
            
            // Set new timer
            this.batchTimer = setTimeout(() => {
                this.sendBatch();
            }, trackingConfig.batchTimeout);
        },
        
        sendBatch: function() {
            if (this.batch.length === 0) return;
            
            var batchData = {
                eventType: 'batch',
                sessionId: sessionManager.getSessionId(),
                visitorId: sessionManager.getVisitorId(),
                siteId: config.client_id,
                timestamp: new Date().toISOString(),
                events: this.batch.slice(), // Copy the batch
                privacy_level: config.privacy_level,
                page: {
                    title: document.title,
                    url: window.location.href,
                    path: window.location.pathname,
                    referrer: document.referrer || 'direct'
                }
            };
            
            // Apply privacy filters based on configuration
            if (config.privacy_level === 'gdpr' || config.privacy_level === 'hipaa') {
                batchData = this.applyPrivacyFilters(batchData);
            }
            
            this.sendToAPI(batchData);
            
            // Clear batch
            this.batch = [];
            if (this.batchTimer) {
                clearTimeout(this.batchTimer);
                this.batchTimer = null;
            }
        },
        
        applyPrivacyFilters: function(data) {
            // Remove or hash sensitive data based on privacy level
            if (config.ip_collection && !config.ip_collection.enabled) {
                // IP collection disabled - will be handled server-side
            }
            
            // Filter PII from event data
            data.events = data.events.map(function(event) {
                if (event.eventData && typeof event.eventData === 'object') {
                    var filtered = {};
                    for (var key in event.eventData) {
                        // Skip fields that might contain PII
                        if (!key.match(/(email|phone|ssn|credit|password|social)/i)) {
                            filtered[key] = event.eventData[key];
                        }
                    }
                    event.eventData = filtered;
                }
                return event;
            });
            
            return data;
        },
        
        sendToAPI: function(data) {
            // Use sendBeacon if available (better for page unload)
            if (navigator.sendBeacon) {
                navigator.sendBeacon(trackingConfig.apiEndpoint, JSON.stringify(data));
            } else {
                // Fallback to fetch
                fetch(trackingConfig.apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data),
                    keepalive: true
                }).catch(function(error) {
                    console.warn('[Evothesis] Failed to send tracking data:', error);
                });
            }
        }
    };
    
    // Tracking functions
    var tracker = {
        trackPageView: function() {
            eventBatcher.addEvent('pageview', {
                page: {
                    title: document.title,
                    url: window.location.href,
                    path: window.location.pathname
                },
                attribution: this.getAttribution()
            });
        },
        
        getAttribution: function() {
            var params = new URLSearchParams(window.location.search);
            return {
                utm_source: params.get('utm_source'),
                utm_medium: params.get('utm_medium'),
                utm_campaign: params.get('utm_campaign'),
                utm_content: params.get('utm_content'),
                utm_term: params.get('utm_term'),
                referrer: document.referrer || 'direct'
            };
        }
    };
    
    // Initialize tracking based on enabled features
    if (config.features && config.features.page_tracking !== false) {
        // Track initial page view
        tracker.trackPageView();
        
        // Track click events
        if (config.features.click_tracking !== false) {
            document.addEventListener('click', function(event) {
                eventBatcher.addEvent('click', {
                    element: event.target.tagName.toLowerCase(),
                    id: event.target.id || null,
                    classes: event.target.className || null,
                    text: (event.target.innerText || '').substring(0, 100)
                });
            });
        }
        
        // Track scroll events
        if (config.features.scroll_tracking === true) {
            var scrollTimeout;
            window.addEventListener('scroll', function() {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(function() {
                    var scrollPercentage = Math.round(
                        (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100
                    );
                    eventBatcher.addEvent('scroll', {
                        scroll_percentage: scrollPercentage
                    });
                }, 250);
            });
        }
        
        // Track form interactions
        if (config.features.form_tracking === true) {
            document.addEventListener('focus', function(event) {
                if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                    eventBatcher.addEvent('form_focus', {
                        field: event.target.name || event.target.id || 'unknown',
                        type: event.target.type || 'text'
                    });
                }
            }, true);
        }
    }
    
    // Send any remaining events before page unload
    window.addEventListener('beforeunload', function() {
        eventBatcher.sendBatch();
    });
    
    // Consent helper function
    function hasUserConsent() {
        // Check common consent management platforms
        if (typeof window.gtag !== 'undefined') {
            // Google Consent Mode
            return window.gtag('consent', 'query', 'analytics_storage') === 'granted';
        }
        
        // Check for basic consent cookie
        return document.cookie.indexOf('evothesis_consent=true') !== -1;
    }
    
    console.log('[Evothesis] Analytics pixel loaded for client:', config.client_id);
})();
"""

def generate_pixel_javascript(config: Dict[str, Any]) -> str:
    """Generate client-specific tracking pixel JavaScript"""
    
    # Get base template
    pixel_code = get_base_tracking_code()
    
    # Inject client configuration
    config_json = json.dumps(config, indent=2)
    pixel_code = pixel_code.replace('{CONFIG_PLACEHOLDER}', config_json)
    
    return pixel_code

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
        
        # Get domain and resolve client_id
        site_id = event_data.get("siteId", event_data.get("site_id", "unknown"))
        client_id = await get_client_id_for_domain(site_id)
        
        events_to_insert = []
        event_count = 0
        
        # Check if this is a batch event
        if event_data.get("eventType") == "batch":
            # Process batch events
            events_to_insert = process_batch_events(event_data, client_ip, user_agent, client_id)
            event_count = len(events_to_insert)
        else:
            # Process single event
            event_timestamp = parse_timestamp(event_data.get("timestamp", ""))
            event_record = create_event_record(event_data, client_ip, user_agent, event_timestamp, client_id)
            events_to_insert = [event_record]
            event_count = 1
        
        # Bulk insert all events in a single transaction
        if events_to_insert:
            try:
                db.bulk_insert_mappings(EventLog, events_to_insert)
                db.commit()
                logger.info(f"Bulk inserted {event_count} events for client {client_id} from site {site_id}")
                
                return {
                    "status": "success",
                    "message": f"{event_count} event(s) received and stored",
                    "events_processed": event_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as db_error:
                logger.error(f"Database bulk insert failed: {str(db_error)}")
                db.rollback()
                return {"status": "error", "message": "Database storage failed"}
        else:
            return {"status": "success", "message": "No events to process", "timestamp": datetime.utcnow().isoformat()}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Event collection failed: {str(e)}")
        return {"status": "error", "message": "Event processing failed"}

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
# Dynamic Pixel Endpoint
# ============================================================================

@app.get("/pixel/{client_id}/tracking.js")
async def get_tracking_pixel(client_id: str):
    """
    Serve dynamically generated tracking pixel JavaScript for a specific client.
    
    This endpoint:
    1. Fetches client configuration from pixel management service
    2. Generates client-specific JavaScript with privacy settings applied
    3. Returns JavaScript with proper content-type headers
    4. Enables hot updates without client-side changes
    """
    try:
        # Get client configuration
        config = await get_client_config(client_id)
        
        # Generate pixel JavaScript
        pixel_js = generate_pixel_javascript(config)
        
        logger.info(f"Generated pixel for client {client_id} with privacy level {config.get('privacy_level', 'standard')}")
        
        # Return JavaScript with proper headers
        return Response(
            content=pixel_js,
            media_type="application/javascript",
            headers={
                "Cache-Control": "public, max-age=300",  # 5 minute browser cache
                "Content-Type": "application/javascript; charset=utf-8",
                "X-Client-ID": client_id,
                "X-Privacy-Level": config.get('privacy_level', 'standard')
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (404, 502, etc.)
        raise
    except Exception as e:
        logger.error(f"Failed to generate pixel for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate tracking pixel")

# ============================================================================
# Cache Management Endpoints (for debugging/ops)
# ============================================================================

@app.post("/pixel/cache/clear")
async def clear_pixel_cache():
    """Clear the configuration cache (useful for debugging)"""
    config_cache.clear()
    return {"message": "Configuration cache cleared"}

@app.get("/pixel/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    current_time = time.time()
    cache_stats = {
        "total_entries": len(config_cache.cache),
        "entries": []
    }
    
    for key, (data, timestamp) in config_cache.cache.items():
        cache_stats["entries"].append({
            "client_id": key,
            "age_seconds": int(current_time - timestamp),
            "expires_in_seconds": int(config_cache.ttl_seconds - (current_time - timestamp)),
            "privacy_level": data.get("privacy_level", "unknown")
        })
    
    return cache_stats

# ============================================================================
# S3 Export Endpoints (existing functionality)
# ============================================================================

# Initialize S3 exporter
s3_exporter = create_s3_exporter()

@app.post("/export/run")
async def trigger_export(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger manual S3 export"""
    try:
        # Run export in background
        background_tasks.add_task(s3_exporter.export_events, db)
        return {"message": "Export started", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Failed to start export: {e}")
        raise HTTPException(status_code=500, detail="Export failed to start")

@app.get("/export/status")
async def get_export_status():
    """Get export status"""
    try:
        status = s3_exporter.get_status()
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