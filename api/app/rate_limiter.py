# Create new file: api/app/rate_limiter.py

import time
import threading
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory rate limiting middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        # IP -> deque of (timestamp, endpoint) tuples
        self.request_history: Dict[str, Deque[Tuple[float, str]]] = defaultdict(deque)
        self.lock = threading.Lock()
        self.last_cleanup = time.time()
        
        # Rate limits (requests per minute)
        self.limits = {
            "/api/v1/admin/": 30,
            "/api/v1/config/": 60, 
            "/pixel/": 100
        }
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded IP first (load balancer/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
            
        return request.client.host
    
    def get_rate_limit(self, path: str) -> int:
        """Get rate limit for path, return 0 for unlimited"""
        for prefix, limit in self.limits.items():
            if path.startswith(prefix):
                return limit
        return 0  # No limit
    
    def cleanup_expired(self, current_time: float):
        """Remove entries older than 1 minute"""
        cutoff = current_time - 60  # 1 minute ago
        
        for ip in list(self.request_history.keys()):
            history = self.request_history[ip]
            
            # Remove old entries
            while history and history[0][0] < cutoff:
                history.popleft()
                
            # Remove empty deques
            if not history:
                del self.request_history[ip]
    
    def is_rate_limited(self, ip: str, path: str, current_time: float) -> Tuple[bool, int]:
        """Check if IP is rate limited for this path"""
        limit = self.get_rate_limit(path)
        if limit == 0:  # No limit
            return False, 0
            
        with self.lock:
            # Cleanup every 5 minutes
            if current_time - self.last_cleanup > 300:
                self.cleanup_expired(current_time)
                self.last_cleanup = current_time
            
            history = self.request_history[ip]
            cutoff = current_time - 60  # Last minute
            
            # Count requests in last minute for this endpoint category
            count = sum(1 for timestamp, _ in history if timestamp >= cutoff)
            
            if count >= limit:
                # Calculate retry after (seconds until oldest request expires)
                if history:
                    oldest_timestamp = min(timestamp for timestamp, _ in history if timestamp >= cutoff)
                    retry_after = int(60 - (current_time - oldest_timestamp)) + 1
                else:
                    retry_after = 60
                return True, retry_after
            
            # Add this request
            history.append((current_time, path))
            return False, 0
    
    async def dispatch(self, request: Request, call_next):
        """Rate limit check"""
        ip = self.get_client_ip(request)
        path = request.url.path
        current_time = time.time()
        
        # Skip rate limiting for health checks
        if path == "/health":
            return await call_next(request)
        
        # Check rate limit
        is_limited, retry_after = self.is_rate_limited(ip, path, current_time)
        
        if is_limited:
            logger.warning(f"Rate limit exceeded for IP {ip} on {path}")
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": retry_after},
                headers={"Retry-After": str(retry_after)}
            )
        
        return await call_next(request)