"""
User Error Logging Middleware
Automatically logs errors for individual users in 100+ user environment
"""
import logging
import traceback
import asyncio
from datetime import datetime
from typing import Callable, Dict, Any
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.monitoring.individual_user_debug import (
    individual_user_debugger,
    DebugLevel,
    ErrorCategory
)

# Configure logger
error_logger = logging.getLogger("user_error_logging")

class UserErrorLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log user errors for debugging"""
    
    def __init__(self, app, debug_enabled: bool = True):
        super().__init__(app)
        self.debug_enabled = debug_enabled
        self.error_categories = {
            # HTTP status code to error category mapping
            400: ErrorCategory.VALIDATION,
            401: ErrorCategory.AUTHENTICATION,
            403: ErrorCategory.PERMISSION,
            404: ErrorCategory.VALIDATION,
            422: ErrorCategory.VALIDATION,
            429: ErrorCategory.RATE_LIMIT,
            500: ErrorCategory.DATABASE,
            502: ErrorCategory.NETWORK,
            503: ErrorCategory.NETWORK,
            504: ErrorCategory.NETWORK,
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log errors for individual users"""
        start_time = datetime.now()
        user_id = None
        user_email = "unknown"
        
        try:
            # Extract user information from request
            user_id, user_email = await self._extract_user_info(request)
            
            # Process request
            response = await call_next(request)
            
            # Log successful activity
            if user_id and self.debug_enabled:
                await self._log_user_activity(
                    user_id=user_id,
                    user_email=user_email,
                    request=request,
                    response=response,
                    start_time=start_time,
                    success=True
                )
            
            return response
            
        except HTTPException as e:
            # Handle HTTP exceptions
            if user_id and self.debug_enabled:
                await self._log_user_error(
                    user_id=user_id,
                    user_email=user_email,
                    request=request,
                    error=e,
                    start_time=start_time,
                    error_category=self.error_categories.get(e.status_code, ErrorCategory.UNKNOWN)
                )
            
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
            
        except Exception as e:
            # Handle unexpected errors
            if user_id and self.debug_enabled:
                await self._log_user_error(
                    user_id=user_id,
                    user_email=user_email,
                    request=request,
                    error=e,
                    start_time=start_time,
                    error_category=ErrorCategory.UNKNOWN
                )
            
            error_logger.error(f"Unexpected error for user {user_id}: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
    
    async def _extract_user_info(self, request: Request) -> tuple[int | None, str]:
        """Extract user ID and email from request"""
        try:
            # Try to get user from JWT token
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                
                # Decode JWT token (simplified - in production, use proper JWT validation)
                import jwt
                from app.core.config import settings
                
                try:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                    user_email = payload.get("sub")  # sub contains email, not user_id
                    user_id = payload.get("user_id")  # Try to get actual user_id if present
                    
                    if user_email:
                        # If we have user_id, use it; otherwise use email hash as ID
                        if user_id:
                            return int(user_id), user_email
                        else:
                            # Use email hash as a consistent ID for logging
                            import hashlib
                            user_id = int(hashlib.md5(user_email.encode()).hexdigest()[:8], 16)
                            return user_id, user_email
                except jwt.InvalidTokenError:
                    pass
            
            # Try to get user from query parameters (for debugging)
            user_id = request.query_params.get("user_id")
            if user_id:
                return int(user_id), "debug_user"
            
            # Try to get user from request body (for debugging)
            if hasattr(request, '_json') and request._json:
                user_id = request._json.get("user_id")
                if user_id:
                    return int(user_id), "debug_user"
            
            return None, "unknown"
            
        except Exception as e:
            error_logger.error(f"Error extracting user info: {e}")
            return None, "unknown"
    
    async def _log_user_activity(
        self,
        user_id: int,
        user_email: str,
        request: Request,
        response: Response,
        start_time: datetime,
        success: bool
    ):
        """Log user activity for debugging"""
        try:
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Extract request data
            request_data = {
                "method": request.method,
                "url": str(request.url),
                "endpoint": request.url.path,
                "query_params": dict(request.query_params),
                "headers": dict(request.headers),
                "client_ip": request.client.host if request.client else "unknown"
            }
            
            # Log activity
            await individual_user_debugger.log_user_activity(
                user_id=user_id,
                email=user_email,
                action=f"{request.method} {request.url.path}",
                endpoint=request.url.path,
                request_data=request_data,
                response_status=response.status_code,
                response_time=response_time,
                success=success
            )
            
        except Exception as e:
            error_logger.error(f"Error logging user activity: {e}")
    
    async def _log_user_error(
        self,
        user_id: int,
        user_email: str,
        request: Request,
        error: Exception,
        start_time: datetime,
        error_category: ErrorCategory
    ):
        """Log user error for debugging"""
        try:
            # Determine severity based on error type
            severity = DebugLevel.ERROR
            if isinstance(error, HTTPException):
                if error.status_code < 500:
                    severity = DebugLevel.WARNING
                else:
                    severity = DebugLevel.ERROR
            else:
                severity = DebugLevel.CRITICAL
            
            # Extract request data
            request_data = {
                "method": request.method,
                "url": str(request.url),
                "endpoint": request.url.path,
                "query_params": dict(request.query_params),
                "headers": dict(request.headers),
                "client_ip": request.client.host if request.client else "unknown"
            }
            
            # Extract response data
            response_data = {
                "status_code": getattr(error, 'status_code', 500),
                "detail": str(error),
                "type": type(error).__name__
            }
            
            # Generate session ID
            session_id = f"session_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Log error
            await individual_user_debugger.log_user_error(
                user_id=user_id,
                email=user_email,
                error_category=error_category,
                error_message=str(error),
                stack_trace=traceback.format_exc(),
                request_data=request_data,
                response_data=response_data,
                session_id=session_id,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
                severity=severity
            )
            
        except Exception as e:
            error_logger.error(f"Error logging user error: {e}")

# Helper function to manually log errors
async def log_user_error_manually(
    user_id: int,
    user_email: str,
    error_category: ErrorCategory,
    error_message: str,
    request_data: Dict[str, Any],
    response_data: Dict[str, Any],
    session_id: str,
    ip_address: str,
    user_agent: str,
    severity: DebugLevel = DebugLevel.ERROR
):
    """Manually log a user error (for use in API endpoints)"""
    try:
        await individual_user_debugger.log_user_error(
            user_id=user_id,
            email=user_email,
            error_category=error_category,
            error_message=error_message,
            stack_trace=traceback.format_exc(),
            request_data=request_data,
            response_data=response_data,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            severity=severity
        )
    except Exception as e:
        error_logger.error(f"Error manually logging user error: {e}")

# Helper function to log user activity manually
async def log_user_activity_manually(
    user_id: int,
    user_email: str,
    action: str,
    endpoint: str,
    request_data: Dict[str, Any],
    response_status: int,
    response_time: float,
    success: bool,
    error_message: str | None = None
):
    """Manually log user activity (for use in API endpoints)"""
    try:
        await individual_user_debugger.log_user_activity(
            user_id=user_id,
            email=user_email,
            action=action,
            endpoint=endpoint,
            request_data=request_data,
            response_status=response_status,
            response_time=response_time,
            success=success,
            error_message=error_message
        )
    except Exception as e:
        error_logger.error(f"Error manually logging user activity: {e}")
