# Updated api/app/error_handler.py - Remove redundant handlers

from fastapi import Request
from fastapi.responses import JSONResponse
import logging
import traceback
import os

logger = logging.getLogger(__name__)

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

# Also update api/app/main.py imports and registration:
# REMOVE: custom_http_exception_handler import
# REMOVE: app.add_exception_handler(HTTPException, custom_http_exception_handler)
# KEEP: app.add_exception_handler(Exception, custom_general_exception_handler)