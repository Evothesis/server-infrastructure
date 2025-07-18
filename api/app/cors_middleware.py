# Updated api/app/cors_middleware.py - Handle Cloud Run cold starts

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, List
import httpx
import logging
import os
import threading
import time
import asyncio

logger = logging.getLogger(__name__)

class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """Dynamic CORS middleware that fetches allowed origins from pixel-management with cold start resilience"""
    
    def __init__(self, app, pixel_management_url: str):
        super().__init__(app)
        self.pixel_management_url = pixel_management_url
        self.cache: Optional[dict] = None
        self.cache_timestamp: float = 0
        self.cache_ttl: int = 600  # 10 minutes (increased from 5 for resilience)
        self._lock = threading.Lock()
        
        # Retry configuration for cold starts
        self.max_retries = 3
        self.initial_timeout = 15.0  # Increased from 5.0 for cold starts
        self.retry_delay = 2.0  # seconds between retries
        
    def extract_domain_from_origin(self, origin: str) -> str:
        """Extract domain from origin header (strips protocol and port)"""
        if not origin:
            return ""
        
        # Remove protocol
        domain = origin.replace("http://", "").replace("https://", "")
        
        # Remove port if present
        domain = domain.split(":")[0]
        
        return domain.lower()
        
    async def get_allowed_origins_with_retry(self) -> List[str]:
        """Get allowed origins with retry logic for cold start resilience"""
        current_time = time.time()
        
        # Thread-safe cache check
        with self._lock:
            if (self.cache and 
                current_time - self.cache_timestamp < self.cache_ttl):
                return self.cache.get("domains", [])
        
        # Fetch from pixel-management with retry logic
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Progressive timeout increase for retries
                timeout = self.initial_timeout + (attempt * 5.0)
                
                logger.info(f"Fetching CORS origins from pixel-management (attempt {attempt + 1}/{self.max_retries}, timeout: {timeout}s)")
                
                async with httpx.AsyncClient(timeout=timeout) as client:
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
                        
                        logger.info(f"Successfully updated CORS allowed origins: {len(domains)} domains (attempt {attempt + 1})")
                        return domains
                    else:
                        last_error = f"HTTP {response.status_code}"
                        logger.warning(f"Pixel-management returned HTTP {response.status_code} (attempt {attempt + 1})")
                        
            except httpx.TimeoutException as e:
                last_error = f"Timeout after {timeout}s"
                logger.warning(f"Pixel-management timeout after {timeout}s (attempt {attempt + 1}) - likely cold start")
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Pixel-management error: {e} (attempt {attempt + 1})")
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
        
        # All retries failed
        logger.error(f"Failed to fetch CORS origins after {self.max_retries} attempts. Last error: {last_error}")
        
        # Return cached domains if available (stale cache is better than no access)
        with self._lock:
            if self.cache:
                stale_domains = self.cache.get("domains", [])
                logger.warning(f"Using stale CORS cache with {len(stale_domains)} domains due to pixel-management unavailability")
                return stale_domains
        
        # Fail secure - no fallback
        logger.error("No CORS origins available and no cache - denying all cross-origin requests")
        return []
    
    async def get_allowed_origins(self) -> List[str]:
        """Get allowed origins with thread-safe caching and retry logic"""
        return await self.get_allowed_origins_with_retry()
    
    async def dispatch(self, request: Request, call_next):
        """Handle CORS for all requests with cold start resilience"""
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            allowed_domains = await self.get_allowed_origins()
            
            if origin:
                origin_domain = self.extract_domain_from_origin(origin)
                
                if origin_domain in allowed_domains:
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
                    logger.warning(f"CORS preflight rejected for origin: {origin} (domain: {origin_domain})")
                    return Response(status_code=403)
            else:
                logger.warning("CORS preflight rejected: no origin header")
                return Response(status_code=403)
        
        # Process actual request
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin:
            allowed_domains = await self.get_allowed_origins()
            origin_domain = self.extract_domain_from_origin(origin)
            
            if origin_domain in allowed_domains:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Expose-Headers"] = "X-Client-ID, X-Authorized-Domain, X-Privacy-Level"
            else:
                logger.warning(f"CORS response blocked for unauthorized origin: {origin} (domain: {origin_domain})")
        
        return response