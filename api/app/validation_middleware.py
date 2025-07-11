# Create new file: api/app/validation_middleware.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request size and content-type validation"""
    
    def __init__(self, app):
        super().__init__(app)
        self.max_request_size = 1024 * 1024  # 1MB
        self.protected_endpoints = ['/collect']
    
    async def dispatch(self, request: Request, call_next):
        """Validate request before processing"""
        
        # Skip validation for non-protected endpoints
        if not any(request.url.path.startswith(endpoint) for endpoint in self.protected_endpoints):
            return await call_next(request)
        
        # Check request size
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    logger.warning(f"Request too large: {size} bytes from {request.client.host}")
                    return JSONResponse(
                        status_code=413,
                        content={"error": "Request too large", "max_size": "1MB"}
                    )
            except ValueError:
                pass
        
        # Check content type for POST requests
        if request.method == "POST":
            content_type = request.headers.get('content-type', '')
            if not content_type.startswith('application/json'):
                logger.warning(f"Invalid content type: {content_type} from {request.client.host}")
                return JSONResponse(
                    status_code=415,
                    content={"error": "Content-Type must be application/json"}
                )
        
        return await call_next(request)