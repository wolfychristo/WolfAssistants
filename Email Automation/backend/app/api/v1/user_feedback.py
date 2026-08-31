from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db, SessionLocal
from app.models.user import User
from app.core.config import settings

router = APIRouter()

class DeletionFeedbackRequest(BaseModel):
    category: str  # pricing, features, support, usability, other
    custom_category: Optional[str] = None  # custom reason when category is 'other'
    rating: int  # 1-5 scale
    details: str
    improvements: Optional[str] = None
    competitor: Optional[str] = None
    contact_consent: bool = False
    contact_method: Optional[str] = None  # email, phone, other

def _get_user_from_request(request: Request, db: Session) -> User:
    """Get user from request token."""
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth.split(' ', 1)[1]
    from jose import jwt
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get('sub')
        if not email:
            raise Exception('no sub')
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/deletion-feedback")
def submit_deletion_feedback(
    feedback: DeletionFeedbackRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Submit detailed feedback before account deletion."""
    user = _get_user_from_request(request, db)
    
    # Validate rating
    if not 1 <= feedback.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Validate category
    valid_categories = ["pricing", "features", "support", "usability", "performance", "other"]
    if feedback.category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {valid_categories}")
    
    # Update user with feedback
    user.deletion_feedback_category = feedback.category
    user.deletion_feedback_custom_category = feedback.custom_category
    user.deletion_feedback_rating = feedback.rating
    user.deletion_feedback_details = feedback.details
    user.deletion_feedback_improvements = feedback.improvements
    user.deletion_feedback_competitor = feedback.competitor
    user.deletion_feedback_contact_consent = feedback.contact_consent
    user.deletion_feedback_contact_method = feedback.contact_method
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Feedback submitted successfully",
        "feedback_id": user.id,
        "category": feedback.category,
        "rating": feedback.rating
    }

@router.get("/deletion-feedback")
def get_deletion_feedback(request: Request, db: Session = Depends(get_db)):
    """Get user's current deletion feedback (if any)."""
    user = _get_user_from_request(request, db)
    
    return {
        "has_feedback": bool(user.deletion_feedback_category),
        "category": user.deletion_feedback_category,
        "custom_category": user.deletion_feedback_custom_category,
        "rating": user.deletion_feedback_rating,
        "details": user.deletion_feedback_details,
        "improvements": user.deletion_feedback_improvements,
        "competitor": user.deletion_feedback_competitor,
        "contact_consent": user.deletion_feedback_contact_consent,
        "contact_method": user.deletion_feedback_contact_method
    }

@router.delete("/account")
def delete_account_with_feedback(
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete user account after feedback has been collected."""
    user = _get_user_from_request(request, db)
    
    # Check if feedback has been submitted
    if not user.deletion_feedback_category:
        raise HTTPException(
            status_code=400, 
            detail="Please provide feedback before deleting your account"
        )
    
    # Soft delete the user
    deletion_time = datetime.utcnow()
    user.deleted_at = deletion_time
    user.deletion_reason = f"User-initiated deletion - Category: {user.deletion_feedback_category}, Rating: {user.deletion_feedback_rating}"
    user.is_active = False
    
    db.commit()
    
    return {
        "message": "Account deleted successfully",
        "deletion_date": deletion_time.isoformat(),
        "feedback_category": user.deletion_feedback_category,
        "feedback_rating": user.deletion_feedback_rating
    }
