# Create new file: api/app/cors_middleware.py

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, List
import httpx
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """Dynamic CORS middleware that fetches allowed origins from pixel-management"""
    
    def __init__(self, app, pixel_management_url: str):
        super().__init__(app)
        self.pixel_management_url = pixel_management_url
        self.cache: Optional[dict] = None
        self.cache_timestamp: float = 0
        self.cache_ttl: int = 300  # 5 minutes
        self._lock = threading.Lock()
        
    async def get_allowed_origins(self) -> List[str]:
        """Get allowed origins with thread-safe caching"""
        current_time = time.time()
        
        # Thread-safe cache check
        with self._lock:
            if (self.cache and 
                current_time - self.cache_timestamp < self.cache_ttl):
                return self.cache.get("domains", [])
        
        # Fetch from pixel-management (keep existing logic)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.pixel_management_url}/api/v1/domains/all"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    domains = data.get("domains", [])
                    
                    # Thread-safe cache update
                    with self._lock:
                        self.cache = {"domains": domains}
                        self.cache_timestamp = current_time
                    
                    logger.info(f"Updated CORS allowed origins: {len(domains)} domains")
                    return domains
                else:
                    logger.warning(f"Failed to fetch domains: HTTP {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error fetching allowed origins: {e}")
        
        # Fallback (keep existing)
        fallback_origins = [
            "http://localhost:3000",
            "http://localhost:8080", 
            "http://localhost:8001",
            "http://localhost"
        ]
        
        logger.warning("Using fallback CORS origins for development")
        return fallback_origins
    
    async def dispatch(self, request: Request, call_next):
        """Handle CORS for all requests"""
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            allowed_origins = await self.get_allowed_origins()
            
            if origin in allowed_origins:
                return Response(
                    status_code=200,
                    headers={
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                        "Access-Control-Max-Age": "3600"
                    }
                )
            else:
                logger.warning(f"CORS preflight rejected for origin: {origin}")
                return Response(status_code=403)
        
        # Process actual request
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin:
            allowed_origins = await self.get_allowed_origins()
            
            if origin in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Expose-Headers"] = "X-Client-ID, X-Authorized-Domain, X-Privacy-Level"
            else:
                logger.warning(f"CORS response blocked for unauthorized origin: {origin}")
        
        return response