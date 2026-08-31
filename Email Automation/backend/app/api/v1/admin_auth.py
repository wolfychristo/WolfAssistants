"""
Admin Authentication System
Provides secure authentication for admin panel access
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.database import get_db, SessionLocal
from app.models.user import User
from app.core.config import settings

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def create_admin_token(user: User) -> str:
    """Create a JWT token for admin user."""
    payload = {
        "sub": user.email,
        "is_admin": user.is_admin,
        "user_id": user.id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)  # 24 hour expiry
    }
    try:
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        print(f"JWT token created successfully for user: {user.email}")
        return token
    except Exception as e:
        print(f"JWT token creation failed: {e}")
        raise HTTPException(status_code=500, detail="Token creation failed")

def verify_admin_token(token: str) -> Optional[User]:
    """Verify admin token and return user if valid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        is_admin = payload.get("is_admin", False)
        
        if not email or not is_admin:
            print(f"JWT verification failed: email={email}, is_admin={is_admin}")
            return None
            
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if user and user.is_admin and user.is_active:
                print(f"JWT verification successful for user: {email}")
                return user
            print(f"User not found or not admin: {email}, user={user}, is_admin={user.is_admin if user else None}")
            return None
        finally:
            db.close()
            
    except jwt.ExpiredSignatureError as e:
        print(f"JWT expired: {e}")
        return None
    except InvalidTokenError as e:
        print(f"JWT error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in JWT verification: {e}")
        return None

def get_current_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current admin user from token."""
    token = credentials.credentials
    user = verify_admin_token(token)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

class AdminLoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def admin_login(
    login_data: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """Admin login endpoint."""
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    
    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create admin token
    token = create_admin_token(user)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin
        }
    }

@router.get("/me")
def get_admin_profile(current_user: User = Depends(get_current_admin_user)):
    """Get current admin user profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

@router.post("/logout")
def admin_logout():
    """Admin logout endpoint (client-side token removal)."""
    return {"message": "Logged out successfully"}
