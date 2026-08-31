"""
User Access Control Middleware
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import SessionLocal
from app.models.user import User
from app.models.user_activity import UserBan, BanStatus

async def check_user_access_control(request: Request, call_next):
    """Middleware to check if user is banned and deny access if so"""
    
    # Skip access control for certain paths
    skip_paths = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/forgot-password-otp",
        "/api/v1/auth/verify-reset-otp",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/reset-password-otp",
        "/api/v1/admin/login",  # Admin login should still work
    ]
    
    if any(request.url.path.startswith(path) for path in skip_paths):
        response = await call_next(request)
        return response
    
    # Check for authentication token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        response = await call_next(request)
        return response
    
    try:
        # Extract token
        token = auth_header.split(' ', 1)[1]
        
        # Decode token to get user email
        from jose import jwt
        from app.core.config import settings
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_email = payload.get('sub')
        
        if not user_email:
            response = await call_next(request)
            return response
        
        # Check if user is banned
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == user_email).first()
            
            if user and user.is_banned():
                # Get active ban details
                active_ban = user.get_active_ban()
                
                ban_details = {
                    "banned": True,
                    "reason": active_ban.reason.value if active_ban else "Unknown",
                    "description": active_ban.description if active_ban else "Account suspended",
                    "banned_at": active_ban.banned_at.isoformat() if active_ban else None,
                    "expires_at": active_ban.expires_at.isoformat() if active_ban and active_ban.expires_at else None,
                    "appeal_available": active_ban.status == BanStatus.ACTIVE if active_ban else False
                }
                
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Account access denied",
                        "ban_details": ban_details,
                        "message": "Your account has been suspended. Please contact support for assistance."
                    }
                )
            
        finally:
            db.close()
    
    except Exception:
        # If there's any error in token processing, let the request continue
        # The authentication middleware will handle it
        pass
    
    response = await call_next(request)
    return response
