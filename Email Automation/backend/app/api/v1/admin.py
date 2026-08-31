from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, text
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pydantic import BaseModel
import logging

from app.core.database import get_db, SessionLocal, AccountsSessionLocal
from app.models.user import User
from app.models.contact import Contact
from app.models.email import Email
from app.models.meeting import Meeting
from app.core.config import settings
from app.middleware.admin_security import require_admin_security
from app.api.v1.admin_auth import get_current_admin_user
from app.core.tenant_database import (
    create_tenant_schema,
    schema_exists,
    get_tenant_schema_name,
    _get_tenant_engine
)

router = APIRouter()
logger = logging.getLogger(__name__)

def _direct_database_admin_update(email: str, is_admin: bool, reason: str = "Admin status changed") -> dict:
    """Direct database update for admin status - immediate effect using Supabase"""
    try:
        db = SessionLocal()
        try:
            # Check if user exists
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                return {"success": False, "error": f"User {email} not found"}
            
            old_admin_status = user.is_admin
            
            # Update admin status directly in database
            user.is_admin = is_admin
            user.updated_at = datetime.utcnow()
            
            db.commit()
            
            # Log the change
            action = "promoted to admin" if is_admin else "removed from admin"
            print(f"DIRECT DATABASE UPDATE: {user.email} {action}")
            print(f"  Reason: {reason}")
            print(f"  Timestamp: {datetime.utcnow()}")
            
            return {
                "success": True,
                "email": user.email,
                "old_admin_status": old_admin_status,
                "new_admin_status": is_admin,
                "action": action,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
        
    except Exception as e:
        print(f"DIRECT DATABASE UPDATE ERROR: {e}")
        return {"success": False, "error": str(e)}

def _get_admin_user(request: Request, db: Session) -> User:
    """Get admin user from request with enhanced security validation."""
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth.split(' ', 1)[1]
    from jose import jwt
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get('sub')
        is_admin = payload.get('is_admin', False)
        
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check JWT payload first for quick validation
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Enhanced security checks
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is inactive")
        
        # Log admin access for security audit
        print(f"SECURITY AUDIT: Admin access by {email} at {datetime.utcnow()}")
        print(f"  IP: {request.client.host if request.client else 'Unknown'}")
        print(f"  User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
        
        return user
    except HTTPException:
        # Re-raise HTTPExceptions (like 403, 404) as-is
        raise
    except Exception as e:
        # Only catch non-HTTP exceptions and convert to 401
        print(f"SECURITY AUDIT: Invalid admin token attempt: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

class UserDeletionRequest(BaseModel):
    user_id: int
    reason: str

class AdminStatusRequest(BaseModel):
    user_id: int
    is_admin: bool
    reason: str = "Admin status changed"

class DirectAdminRequest(BaseModel):
    email: str
    is_admin: bool
    reason: str = "Admin status changed by primary admin"

class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    deleted_users: int
    new_signups_today: int
    new_signups_this_week: int
    new_signups_this_month: int
    deletion_reasons: Dict[str, int]
    tier_distribution: Dict[str, int]
    recent_signups: List[Dict[str, Any]]
    recent_deletions: List[Dict[str, Any]]
    feedback_categories: Dict[str, int]
    average_feedback_rating: float
    feedback_insights: Dict[str, Any]


@router.get("/data")
def get_admin_data():
    """Get admin data without authentication for testing"""
    db = SessionLocal()
    try:
        # Get user counts
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True, User.deleted_at.is_(None)).count()
        deleted_users = db.query(User).filter(User.deleted_at.isnot(None)).count()
        admin_users = db.query(User).filter(User.is_admin == True).count()
        
        # Get feedback data
        users_with_feedback = db.query(User).filter(
            User.deletion_feedback_category.isnot(None)
        ).count()
        
        # Get feedback categories
        from sqlalchemy import func
        feedback_categories = db.query(
            User.deletion_feedback_category,
            func.count(User.id).label('count')
        ).filter(
            User.deletion_feedback_category.isnot(None)
        ).group_by(User.deletion_feedback_category).all()
        
        # Get recent users
        recent_users = db.query(User).order_by(User.created_at.desc()).limit(10).all()
        
        # Get users with feedback
        users_with_feedback_details = db.query(User).filter(
            User.deletion_feedback_category.isnot(None)
        ).limit(10).all()
        
        return {
            "user_stats": {
                "total_users": total_users,
                "active_users": active_users,
                "deleted_users": deleted_users,
                "admin_users": admin_users
            },
            "feedback_stats": {
                "users_with_feedback": users_with_feedback,
                "categories": [{"category": cat, "count": count} for cat, count in feedback_categories]
            },
            "recent_users": [
                {
                    "email": user.email,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active
                } for user in recent_users
            ],
            "feedback_details": [
                {
                    "email": user.email,
                    "category": user.deletion_feedback_category,
                    "rating": user.deletion_feedback_rating,
                    "details": user.deletion_feedback_details,
                    "custom_category": user.deletion_feedback_custom_category
                } for user in users_with_feedback_details
            ]
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@router.get("/stats")
def get_admin_stats(current_user: User = Depends(get_current_admin_user)):
    """Get secured admin statistics."""
    db = SessionLocal()
    try:
        # Get user counts
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True, User.deleted_at.is_(None)).count()
        deleted_users = db.query(User).filter(User.deleted_at.isnot(None)).count()
        admin_users = db.query(User).filter(User.is_admin == True).count()
        
        # Get feedback data
        users_with_feedback = db.query(User).filter(
            User.deletion_feedback_category.isnot(None)
        ).count()
        
        # Get feedback categories
        from sqlalchemy import func
        feedback_categories = db.query(
            User.deletion_feedback_category,
            func.count(User.id).label('count')
        ).filter(
            User.deletion_feedback_category.isnot(None)
        ).group_by(User.deletion_feedback_category).all()
        
        # Get recent users
        recent_users = db.query(User).order_by(User.created_at.desc()).limit(10).all()
        
        # Get users with feedback
        users_with_feedback_details = db.query(User).filter(
            User.deletion_feedback_category.isnot(None)
        ).limit(10).all()
        
        return {
            "user_stats": {
                "total_users": total_users,
                "active_users": active_users,
                "deleted_users": deleted_users,
                "admin_users": admin_users
            },
            "feedback_stats": {
                "users_with_feedback": users_with_feedback,
                "categories": [{"category": cat, "count": count} for cat, count in feedback_categories]
            },
            "recent_users": [
                {
                    "email": user.email,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active
                } for user in recent_users
            ],
            "feedback_details": [
                {
                    "email": user.email,
                    "category": user.deletion_feedback_category,
                    "rating": user.deletion_feedback_rating,
                    "details": user.deletion_feedback_details,
                    "custom_category": user.deletion_feedback_custom_category
                } for user in users_with_feedback_details
            ],
            "admin_user": {
                "email": current_user.email,
                "full_name": current_user.full_name
            }
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@router.get("/users")
def get_all_users(current_user: User = Depends(get_current_admin_user)):
    """Get secured list of all users."""
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.created_at.desc()).all()
        
        users_data = []
        for user in users:
            users_data.append({
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "company_name": user.company_name,
                "pricing_tier": user.pricing_tier,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
                "deletion_reason": user.deletion_reason,
                "is_admin": user.is_admin
            })
        
        return {
            "users": users_data,
            "total": len(users_data),
            "admin_user": {
                "email": current_user.email,
                "full_name": current_user.full_name
            }
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@router.post("/users/{user_id}/delete")
def delete_user(
    user_id: int,
    deletion_request: UserDeletionRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Soft delete a user with reason."""
    admin_user = _get_admin_user(request, db)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.deleted_at:
        raise HTTPException(status_code=400, detail="User already deleted")
    
    # Soft delete
    user.deleted_at = datetime.utcnow()
    user.deletion_reason = deletion_request.reason
    user.is_active = False
    
    db.commit()
    
    return {"message": f"User {user.email} deleted successfully", "deletion_reason": deletion_request.reason}

@router.post("/users/{user_id}/restore")
def restore_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Restore a soft-deleted user."""
    admin_user = _get_admin_user(request, db)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.deleted_at:
        raise HTTPException(status_code=400, detail="User is not deleted")
    
    # Restore user
    user.deleted_at = None
    user.deletion_reason = None
    user.is_active = True
    
    db.commit()
    
    return {"message": f"User {user.email} restored successfully"}

@router.post("/users/{user_id}/admin-status")
def change_admin_status(
    user_id: int,
    admin_request: AdminStatusRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Change admin status of a user. Only primary admin can manage other admins."""
    admin_user = _get_admin_user(request, db)
    
    # Verify primary admin authorization
    if admin_user.email != 'christopherharish88@gmail.com':
        raise HTTPException(
            status_code=403, 
            detail="Only primary admin can manage admin privileges"
        )
    
    # Get the target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-demotion (primary admin protection)
    if admin_user.id == target_user.id and not admin_request.is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Primary admin cannot remove their own admin privileges"
        )
    
    # Use direct database update for immediate effect
    db_result = _direct_database_admin_update(
        target_user.email, 
        admin_request.is_admin, 
        admin_request.reason
    )
    
    if not db_result["success"]:
        raise HTTPException(status_code=500, detail=db_result["error"])
    
    # Log admin status change for security audit
    print(f"SECURITY AUDIT: Admin status changed by {admin_user.email}")
    print(f"  Target: {target_user.email}")
    print(f"  Old Status: {db_result['old_admin_status']}")
    print(f"  New Status: {db_result['new_admin_status']}")
    print(f"  Reason: {admin_request.reason}")
    print(f"  Timestamp: {datetime.utcnow()}")
    
    return {
        "message": f"User {target_user.email} has been {db_result['action']}",
        "user_id": user_id,
        "email": target_user.email,
        "old_admin_status": db_result["old_admin_status"],
        "new_admin_status": db_result["new_admin_status"],
        "reason": admin_request.reason,
        "changed_by": admin_user.email,
        "timestamp": db_result["timestamp"],
        "security_audit": "Admin status change logged and database updated",
        "database_updated": True
    }

@router.get("/users/{user_id}/admin-status")
def get_user_admin_status(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get admin status of a specific user."""
    admin_user = _get_admin_user(request, db)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None
    }

@router.post("/direct-admin-update")
def direct_admin_update(
    admin_request: DirectAdminRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Direct admin status update by email - only primary admin can use this."""
    admin_user = _get_admin_user(request, db)
    
    # Verify primary admin authorization
    if admin_user.email != 'christopherharish88@gmail.com':
        raise HTTPException(
            status_code=403, 
            detail="Only primary admin can perform direct admin updates"
        )
    
    # Prevent self-demotion (primary admin protection)
    if admin_request.email == 'christopherharish88@gmail.com' and not admin_request.is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Primary admin cannot remove their own admin privileges"
        )
    
    # Perform direct database update
    db_result = _direct_database_admin_update(
        admin_request.email, 
        admin_request.is_admin, 
        admin_request.reason
    )
    
    if not db_result["success"]:
        raise HTTPException(status_code=500, detail=db_result["error"])
    
    # Log admin status change for security audit
    print(f"SECURITY AUDIT: Direct admin update by {admin_user.email}")
    print(f"  Target: {admin_request.email}")
    print(f"  Old Status: {db_result['old_admin_status']}")
    print(f"  New Status: {db_result['new_admin_status']}")
    print(f"  Reason: {admin_request.reason}")
    print(f"  Timestamp: {datetime.utcnow()}")
    
    return {
        "message": f"User {admin_request.email} has been {db_result['action']}",
        "email": admin_request.email,
        "old_admin_status": db_result["old_admin_status"],
        "new_admin_status": db_result["new_admin_status"],
        "reason": admin_request.reason,
        "changed_by": admin_user.email,
        "timestamp": db_result["timestamp"],
        "security_audit": "Direct admin update completed",
        "database_updated": True
    }

@router.get("/analytics/signups")
def get_signup_analytics(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get signup analytics for the last N days."""
    admin_user = _get_admin_user(request, db)
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Daily signups
    daily_signups = db.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(
        func.date(User.created_at)
    ).order_by('date').all()
    
    # Signups by tier
    tier_signups = db.query(
        User.pricing_tier,
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(User.pricing_tier).all()
    
    # Signups by source (heard_about_us)
    source_signups = db.query(
        User.heard_about_us,
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date,
        User.heard_about_us.isnot(None)
    ).group_by(User.heard_about_us).all()
    
    return {
        "period_days": days,
        "daily_signups": [{"date": str(date), "count": count} for date, count in daily_signups],
        "tier_signups": [{"tier": tier, "count": count} for tier, count in tier_signups],
        "source_signups": [{"source": source, "count": count} for source, count in source_signups]
    }

@router.get("/analytics/deletions")
def get_deletion_analytics(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get deletion analytics for the last N days."""
    admin_user = _get_admin_user(request, db)
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Daily deletions
    daily_deletions = db.query(
        func.date(User.deleted_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.deleted_at >= start_date
    ).group_by(
        func.date(User.deleted_at)
    ).order_by('date').all()
    
    # Deletions by reason
    reason_deletions = db.query(
        User.deletion_reason,
        func.count(User.id).label('count')
    ).filter(
        User.deleted_at >= start_date
    ).group_by(User.deletion_reason).all()
    
    # Deletions by tier
    tier_deletions = db.query(
        User.pricing_tier,
        func.count(User.id).label('count')
    ).filter(
        User.deleted_at >= start_date
    ).group_by(User.pricing_tier).all()
    
    return {
        "period_days": days,
        "daily_deletions": [{"date": str(date), "count": count} for date, count in daily_deletions],
        "reason_deletions": [{"reason": reason or "No reason", "count": count} for reason, count in reason_deletions],
        "tier_deletions": [{"tier": tier, "count": count} for tier, count in tier_deletions]
    }

@router.get("/feedback-details")
def get_detailed_feedback_data(
    page: int = 1,
    limit: int = 50,
    category: str | None = None,
    min_rating: int | None = None,
    max_rating: int | None = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed feedback data in spreadsheet format."""
    try:
        offset = (page - 1) * limit
        
        # Simple query to test
        users = db.query(User).filter(
            User.deleted_at.isnot(None),
            User.deletion_feedback_category.isnot(None)
        ).limit(limit).all()
        total = len(users)
        
        feedback_data = []
        for user in users:
            feedback_data.append({
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "company_name": user.company_name,
                "pricing_tier": user.pricing_tier,
                "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
                "feedback_category": user.deletion_feedback_category,
                "feedback_custom_category": user.deletion_feedback_custom_category,
                "feedback_rating": user.deletion_feedback_rating,
                "feedback_details": user.deletion_feedback_details,
                "improvements_suggested": user.deletion_feedback_improvements,
                "competitor_switched_to": user.deletion_feedback_competitor,
                "contact_consent": user.deletion_feedback_contact_consent,
                "contact_method": user.deletion_feedback_contact_method,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "account_age_days": (user.deleted_at - user.created_at).days if user.deleted_at and user.created_at else None
            })
        
        return {
            "feedback_data": feedback_data,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
            "filters_applied": {
                "category": category,
                "min_rating": min_rating,
                "max_rating": max_rating
            }
        }
    except Exception as e:
        print(f"Error in feedback-details: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching feedback data: {str(e)}")

@router.get("/feedback-analytics")
def get_feedback_analytics(current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Get comprehensive feedback analytics."""
    try:
        # Category distribution
        category_stats = db.query(
            User.deletion_feedback_category,
            func.count(User.id).label('count'),
            func.avg(User.deletion_feedback_rating).label('avg_rating')
        ).filter(
            User.deleted_at.isnot(None),
            User.deletion_feedback_category.isnot(None)
        ).group_by(User.deletion_feedback_category).all()
        
        # Rating distribution
        rating_stats = db.query(
            User.deletion_feedback_rating,
            func.count(User.id).label('count')
        ).filter(
            User.deleted_at.isnot(None),
            User.deletion_feedback_rating.isnot(None)
        ).group_by(User.deletion_feedback_rating).all()
        
        # Competitor analysis
        competitor_stats = db.query(
            User.deletion_feedback_competitor,
            func.count(User.id).label('count')
        ).filter(
            User.deleted_at.isnot(None),
            User.deletion_feedback_competitor.isnot(None)
        ).group_by(User.deletion_feedback_competitor).all()
        
        # Contact consent analysis
        contact_consent_stats = db.query(
            User.deletion_feedback_contact_consent,
            func.count(User.id).label('count')
        ).filter(
            User.deleted_at.isnot(None)
        ).group_by(User.deletion_feedback_contact_consent).all()
        
        return {
            "category_analysis": [
                {
                    "category": cat,
                    "count": count,
                    "average_rating": round(float(avg_rating), 2) if avg_rating else None
                }
                for cat, count, avg_rating in category_stats
            ],
            "rating_distribution": [
                {"rating": rating, "count": count}
                for rating, count in rating_stats
            ],
            "competitor_analysis": [
                {"competitor": comp, "count": count}
                for comp, count in competitor_stats
            ],
            "contact_consent_analysis": [
                {"consent": consent, "count": count}
                for consent, count in contact_consent_stats
            ]
        }
    except Exception as e:
        print(f"Error in feedback-analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching analytics: {str(e)}")


@router.get("/system/health")
def get_system_health(request: Request, db: Session = Depends(get_db)):
    """Get system health metrics."""
    admin_user = _get_admin_user(request, db)
    
    # Database health
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    # User activity metrics
    active_users_24h = db.query(User).filter(
        User.updated_at >= datetime.utcnow() - timedelta(hours=24),
        User.deleted_at.is_(None)
    ).count()
    
    # Email metrics (if emails table exists)
    try:
        total_emails = db.query(Email).count()
        # Use sent_at field instead of created_at for emails
        emails_today = db.query(Email).filter(
            func.date(Email.sent_at) == datetime.utcnow().date()
        ).count()
    except Exception:
        total_emails = 0
        emails_today = 0
    
    # Meeting metrics (if meetings table exists)
    try:
        total_meetings = db.query(Meeting).count()
        # Use start_time field instead of created_at for meetings
        meetings_today = db.query(Meeting).filter(
            func.date(Meeting.start_time) == datetime.utcnow().date()
        ).count()
    except Exception:
        total_meetings = 0
        meetings_today = 0
    
    return {
        "database_status": db_status,
        "active_users_24h": active_users_24h,
        "total_emails": total_emails,
        "emails_today": emails_today,
        "total_meetings": total_meetings,
        "meetings_today": meetings_today,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/schemas/create-all")
def create_schemas_for_all_users_endpoint(current_user: User = Depends(get_current_admin_user)):
    """Create tenant schemas for all users who don't have one."""
    try:
        # Get all users
        db = AccountsSessionLocal()
        try:
            users = db.query(User).filter(User.deleted_at.is_(None)).all()
            user_emails = [user.email for user in users]
        finally:
            db.close()
        
        if not user_emails:
            return {
                "success": False,
                "message": "No users found",
                "created": 0,
                "skipped": 0,
                "failed": 0
            }
        
        # Check existing schemas
        engine = _get_tenant_engine()
        existing_schemas = set()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name LIKE 'tenant_%'
                """))
                existing_schemas = {row[0] for row in result.fetchall()}
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to check existing schemas: {str(e)}"
            }
        
        # Find users without schemas
        users_without_schemas = []
        for email in user_emails:
            schema_name = get_tenant_schema_name(email)
            if schema_name not in existing_schemas:
                users_without_schemas.append(email)
        
        # Update schema_created flag for users who already have schemas
        updated_flags_count = 0
        accounts_db = AccountsSessionLocal()
        try:
            for email in user_emails:
                schema_name = get_tenant_schema_name(email)
                if schema_name in existing_schemas:
                    # Schema exists, ensure flag is set
                    try:
                        user = accounts_db.query(User).filter(User.email == email).first()
                        if user and not user.schema_created:
                            user.schema_created = True
                            updated_flags_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to update schema_created flag for {email}: {str(e)}")
            
            if updated_flags_count > 0:
                accounts_db.commit()
        finally:
            accounts_db.close()
        
        if not users_without_schemas:
            return {
                "success": True,
                "message": "All users already have tenant schemas",
                "total_users": len(user_emails),
                "created": 0,
                "skipped": len(user_emails),
                "failed": 0,
                "flags_updated": updated_flags_count
            }
        
        # Create schemas
        created_count = 0
        failed_count = 0
        failed_users = []
        
        for email in users_without_schemas:
            try:
                success = create_tenant_schema(email)
                if success:
                    created_count += 1
                else:
                    # Check if it was created (might already exist)
                    if schema_exists(email):
                        created_count += 1
                        # Update flag if schema exists but wasn't created by this call
                        # (create_tenant_schema should handle this, but ensure it's set)
                        accounts_db = AccountsSessionLocal()
                        try:
                            user = accounts_db.query(User).filter(User.email == email).first()
                            if user and not user.schema_created:
                                user.schema_created = True
                                accounts_db.commit()
                        except Exception:
                            pass
                        finally:
                            accounts_db.close()
                    else:
                        failed_count += 1
                        failed_users.append(email)
            except Exception as e:
                failed_count += 1
                failed_users.append(email)
        
        return {
            "success": True,
            "message": f"Schema creation completed",
            "total_users": len(user_emails),
            "users_with_schemas": len(user_emails) - len(users_without_schemas),
            "created": created_count,
            "skipped": len(user_emails) - len(users_without_schemas),
            "failed": failed_count,
            "failed_users": failed_users
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
