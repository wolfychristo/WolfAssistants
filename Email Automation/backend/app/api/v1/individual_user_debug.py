#!/usr/bin/env python3
"""
Minimal individual user debug API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.monitoring.individual_user_debug import individual_user_debugger, DebugLevel, ErrorCategory

router = APIRouter()

@router.get("/health")
def health_check():
    """Health check endpoint for individual user debug"""
    return {"status": "ok", "message": "Individual user debug module is running"}

@router.post("/log-activity")
async def log_activity(
    user_id: int,
    email: str,
    action: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Log user activity"""
    try:
        await individual_user_debugger.log_user_activity(
            user_id=user_id,
            email=email,
            action=action
        )
        return {"status": "success", "message": "Activity logged"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log activity: {str(e)}")

@router.post("/log-error")
async def log_error(
    user_id: int,
    email: str,
    error_category: ErrorCategory,
    error_message: str,
    severity: DebugLevel = DebugLevel.ERROR,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Log user error"""
    try:
        await individual_user_debugger.log_user_error(
            user_id=user_id,
            email=email,
            error_category=error_category,
            error_message=error_message,
            severity=severity
        )
        return {"status": "success", "message": "Error logged"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log error: {str(e)}")
