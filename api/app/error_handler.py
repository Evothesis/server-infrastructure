# Create new file: api/app/error_handler.py

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
import os

logger = logging.getLogger(__name__)

async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with sanitized responses"""
    # Log the full error for debugging
    logger.warning(f"HTTP {exc.status_code} on {request.url}: {exc.detail}")
    
    # Return sanitized response
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

async def custom_general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with sanitized responses"""
    # Log full error details internally
    logger.error(f"Unhandled exception on {request.url}: {str(exc)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Determine if we're in development mode
    is_development = os.getenv("ENVIRONMENT", "development").lower() == "development"
    
    if is_development:
        # In development, provide more details
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        # In production, return generic error
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

# Sanitized error messages for common exceptions
ERROR_MESSAGES = {
    "ConnectionError": "Service temporarily unavailable",
    "TimeoutError": "Request timeout",
    "ValidationError": "Invalid request format",
    "DatabaseError": "Data processing error",
    "AuthenticationError": "Authentication failed",
    "AuthorizationError": "Access denied"
}