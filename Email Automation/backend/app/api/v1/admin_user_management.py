"""
Admin User Management API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.user_activity import (
    UserActivity, UserBan, AbusePattern, AdminNotification,
    ActivityType, BanReason, BanStatus
)
from app.core.user_monitoring import UserMonitoringService
from app.api.v1.admin import _get_admin_user

router = APIRouter()

# Pydantic models for requests
class BanUserRequest(BaseModel):
    user_id: int
    reason: BanReason
    description: str
    ban_duration_days: Optional[int] = None

class UnbanUserRequest(BaseModel):
    user_id: int
    reason: str

class AppealReviewRequest(BaseModel):
    ban_id: int
    action: str  # "approve" or "deny"
    notes: Optional[str] = None

class UserActivityFilter(BaseModel):
    user_id: Optional[int] = None
    activity_type: Optional[ActivityType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_risk_score: Optional[int] = None

@router.get("/users/activities")
def get_user_activities(
    request: Request,
    db: Session = Depends(get_db),
    user_id: Optional[int] = None,
    activity_type: Optional[str] = None,
    days: int = 7,
    limit: int = 100
):
    """Get user activities with filtering options"""
    admin_user = _get_admin_user(request, db)
    
    # Build query
    query = db.query(UserActivity)
    
    if user_id:
        query = query.filter(UserActivity.user_id == user_id)
    
    if activity_type:
        try:
            activity_enum = ActivityType(activity_type)
            query = query.filter(UserActivity.activity_type == activity_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid activity type")
    
    # Date filter
    start_date = datetime.utcnow() - timedelta(days=days)
    query = query.filter(UserActivity.created_at >= start_date)
    
    # Order and limit
    activities = query.order_by(desc(UserActivity.created_at)).limit(limit).all()
    
    return {
        "activities": [
            {
                "id": activity.id,
                "user_id": activity.user_id,
                "activity_type": activity.activity_type.value,
                "description": activity.description,
                "ip_address": activity.ip_address,
                "risk_score": activity.risk_score,
                "created_at": activity.created_at.isoformat(),
                "metadata": activity.activity_metadata
            }
            for activity in activities
        ],
        "total": len(activities)
    }

@router.get("/users/risk-analysis")
def get_user_risk_analysis(
    request: Request,
    db: Session = Depends(get_db),
    user_id: Optional[int] = None
):
    """Get risk analysis for users"""
    admin_user = _get_admin_user(request, db)
    
    monitoring_service = UserMonitoringService(db)
    
    if user_id:
        # Single user analysis
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        risk_score = monitoring_service.get_user_risk_score(user_id)
        
        # Get recent abuse patterns
        abuse_patterns = db.query(AbusePattern).filter(
            and_(
                AbusePattern.user_id == user_id,
                AbusePattern.is_active == True
            )
        ).all()
        
        # Get recent high-risk activities
        high_risk_activities = db.query(UserActivity).filter(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.risk_score >= 50,
                UserActivity.created_at >= datetime.utcnow() - timedelta(days=7)
            )
        ).order_by(desc(UserActivity.created_at)).limit(10).all()
        
        return {
            "user_id": user_id,
            "email": user.email,
            "risk_score": risk_score,
            "is_banned": user.is_banned(),
            "abuse_patterns": [
                {
                    "type": pattern.pattern_type,
                    "severity": pattern.severity,
                    "occurrences": pattern.occurrences,
                    "last_detected": pattern.last_detected.isoformat()
                }
                for pattern in abuse_patterns
            ],
            "high_risk_activities": [
                {
                    "type": activity.activity_type.value,
                    "description": activity.description,
                    "risk_score": activity.risk_score,
                    "created_at": activity.created_at.isoformat()
                }
                for activity in high_risk_activities
            ]
        }
    else:
        # All users risk analysis
        users = db.query(User).filter(User.is_active == True).all()
        
        user_risks = []
        for user in users:
            risk_score = monitoring_service.get_user_risk_score(user.id)
            if risk_score > 0:  # Only include users with some risk
                user_risks.append({
                    "user_id": user.id,
                    "email": user.email,
                    "risk_score": risk_score,
                    "is_banned": user.is_banned()
                })
        
        # Sort by risk score
        user_risks.sort(key=lambda x: x["risk_score"], reverse=True)
        
        return {
            "high_risk_users": user_risks[:20],  # Top 20
            "total_analyzed": len(users)
        }

@router.post("/users/ban")
def ban_user(
    request: Request,
    ban_request: BanUserRequest,
    db: Session = Depends(get_db)
):
    """Ban a user"""
    admin_user = _get_admin_user(request, db)
    
    # Get target user
    target_user = db.query(User).filter(User.id == ban_request.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent banning admins
    if target_user.is_admin:
        raise HTTPException(status_code=403, detail="Cannot ban admin users")
    
    # Check if user is already banned
    if target_user.is_banned():
        raise HTTPException(status_code=400, detail="User is already banned")
    
    # Create ban
    monitoring_service = UserMonitoringService(db)
    ban = monitoring_service.ban_user(
        user_id=ban_request.user_id,
        banned_by=admin_user.id,
        reason=ban_request.reason,
        description=ban_request.description,
        ban_duration_days=ban_request.ban_duration_days
    )
    
    return {
        "message": f"User {target_user.email} has been banned",
        "ban_id": ban.id,
        "reason": ban.reason.value,
        "expires_at": ban.expires_at.isoformat() if ban.expires_at else None,
        "banned_by": admin_user.email
    }

@router.post("/users/unban")
def unban_user(
    request: Request,
    unban_request: UnbanUserRequest,
    db: Session = Depends(get_db)
):
    """Unban a user"""
    admin_user = _get_admin_user(request, db)
    
    # Get target user
    target_user = db.query(User).filter(User.id == unban_request.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is actually banned
    if not target_user.is_banned():
        raise HTTPException(status_code=400, detail="User is not currently banned")
    
    # Unban user
    monitoring_service = UserMonitoringService(db)
    success = monitoring_service.unban_user(
        user_id=unban_request.user_id,
        unbanned_by=admin_user.id,
        reason=unban_request.reason
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to unban user")
    
    return {
        "message": f"User {target_user.email} has been unbanned",
        "unbanned_by": admin_user.email,
        "reason": unban_request.reason
    }

@router.get("/users/bans")
def get_user_bans(
    request: Request,
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    limit: int = 50
):
    """Get list of user bans"""
    admin_user = _get_admin_user(request, db)
    
    query = db.query(UserBan)
    
    if status:
        try:
            status_enum = BanStatus(status)
            query = query.filter(UserBan.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ban status")
    
    bans = query.order_by(desc(UserBan.created_at)).limit(limit).all()
    
    return {
        "bans": [
            {
                "id": ban.id,
                "user_id": ban.user_id,
                "user_email": ban.user.email,
                "reason": ban.reason.value,
                "description": ban.description,
                "status": ban.status.value,
                "banned_at": ban.banned_at.isoformat(),
                "expires_at": ban.expires_at.isoformat() if ban.expires_at else None,
                "banned_by": ban.banned_by_user.email,
                "appeal_submitted_at": ban.appeal_submitted_at.isoformat() if ban.appeal_submitted_at else None
            }
            for ban in bans
        ],
        "total": len(bans)
    }

@router.get("/users/abuse-patterns")
def get_abuse_patterns(
    request: Request,
    db: Session = Depends(get_db),
    user_id: Optional[int] = None,
    days: int = 30
):
    """Get abuse patterns"""
    admin_user = _get_admin_user(request, db)
    
    query = db.query(AbusePattern)
    
    if user_id:
        query = query.filter(AbusePattern.user_id == user_id)
    
    # Date filter
    start_date = datetime.utcnow() - timedelta(days=days)
    query = query.filter(AbusePattern.created_at >= start_date)
    
    patterns = query.order_by(desc(AbusePattern.last_detected)).all()
    
    return {
        "patterns": [
            {
                "id": pattern.id,
                "user_id": pattern.user_id,
                "user_email": pattern.user.email,
                "pattern_type": pattern.pattern_type,
                "severity": pattern.severity,
                "occurrences": pattern.occurrences,
                "first_detected": pattern.first_detected.isoformat(),
                "last_detected": pattern.last_detected.isoformat(),
                "is_active": pattern.is_active,
                "auto_ban_triggered": pattern.auto_ban_triggered
            }
            for pattern in patterns
        ],
        "total": len(patterns)
    }

@router.get("/notifications")
def get_admin_notifications(
    request: Request,
    db: Session = Depends(get_db),
    unread_only: bool = False,
    limit: int = 50
):
    """Get admin notifications"""
    admin_user = _get_admin_user(request, db)
    
    query = db.query(AdminNotification).filter(
        AdminNotification.admin_id == admin_user.id
    )
    
    if unread_only:
        query = query.filter(AdminNotification.is_read == False)
    
    notifications = query.order_by(desc(AdminNotification.created_at)).limit(limit).all()
    
    return {
        "notifications": [
            {
                "id": notification.id,
                "type": notification.notification_type,
                "title": notification.title,
                "message": notification.message,
                "user_id": notification.user_id,
                "user_email": notification.user.email if notification.user else None,
                "priority": notification.priority,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
                "metadata": notification.notification_metadata
            }
            for notification in notifications
        ],
        "total": len(notifications)
    }

@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    admin_user = _get_admin_user(request, db)
    
    notification = db.query(AdminNotification).filter(
        and_(
            AdminNotification.id == notification_id,
            AdminNotification.admin_id == admin_user.id
        )
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read"}

@router.get("/statistics/abuse")
def get_abuse_statistics(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get abuse detection statistics"""
    admin_user = _get_admin_user(request, db)
    
    monitoring_service = UserMonitoringService(db)
    stats = monitoring_service.get_abuse_statistics()
    
    # Add additional statistics
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # High risk users (risk score > 50)
    high_risk_users = db.query(User).filter(
        and_(
            User.is_active == True,
            User.id.in_(
                db.query(UserActivity.user_id).filter(
                    and_(
                        UserActivity.created_at >= thirty_days_ago,
                        UserActivity.risk_score >= 50
                    )
                ).distinct()
            )
        )
    ).count()
    
    stats["high_risk_users"] = high_risk_users
    
    return stats

@router.post("/users/{user_id}/appeal-review")
def review_user_appeal(
    user_id: int,
    appeal_request: AppealReviewRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Review a user's appeal for ban reversal"""
    admin_user = _get_admin_user(request, db)
    
    # Get the ban
    ban = db.query(UserBan).filter(
        and_(
            UserBan.id == appeal_request.ban_id,
            UserBan.user_id == user_id,
            UserBan.status == BanStatus.APPEALED
        )
    ).first()
    
    if not ban:
        raise HTTPException(status_code=404, detail="Appeal not found")
    
    if appeal_request.action == "approve":
        # Approve appeal - unban user
        ban.status = BanStatus.OVERTURNED
        ban.appeal_reviewed_at = datetime.utcnow()
        ban.appeal_reviewed_by = admin_user.id
        ban.appeal_notes = appeal_request.notes
        
        # Reactivate user
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_active = True
        
        message = f"Appeal approved for user {user.email if user else user_id}"
        
    elif appeal_request.action == "deny":
        # Deny appeal - keep ban active
        ban.status = BanStatus.ACTIVE
        ban.appeal_reviewed_at = datetime.utcnow()
        ban.appeal_reviewed_by = admin_user.id
        ban.appeal_notes = appeal_request.notes
        
        message = f"Appeal denied for user {ban.user.email}"
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'deny'")
    
    db.commit()
    
    return {
        "message": message,
        "action": appeal_request.action,
        "reviewed_by": admin_user.email,
        "notes": appeal_request.notes
    }
