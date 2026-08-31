"""
Referral System API endpoints

Handles referral invitations, rewards, and credit management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr
import secrets
import string
import re
import logging
from jose import jwt

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.referral import (
    ReferralInvitation, ReferralReward, UserCredit, ReferralCode,
    ReferralStatus, RewardType, CreditType
)
from app.core.email_service import EmailService

logger = logging.getLogger(__name__)
router = APIRouter()

def _get_owner_from_request(request: Request) -> str:
    """Extract user email from JWT token in Authorization header."""
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(' ', 1)[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get('sub')
        if not email:
            raise Exception('no sub')
        return email
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def _get_current_user_from_request(request: Request, db: Session) -> User:
    """Get current user from JWT token in Authorization header."""
    email = _get_owner_from_request(request)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Pydantic models
class InviteRequest(BaseModel):
    email: EmailStr
    personal_message: Optional[str] = None

class InviteResponse(BaseModel):
    success: bool
    message: str
    referral_code: str
    credits_earned: int

class ReferralStats(BaseModel):
    total_invitations: int
    successful_signups: int
    conversion_rate: float
    total_credits_earned: int
    pending_invitations: int
    recent_activity: List[Dict[str, Any]]

class CreditBalance(BaseModel):
    total_credits: int
    available_credits: int
    used_credits: int
    credits_expiring_soon: int

class CreditHistory(BaseModel):
    id: int
    credit_type: str
    amount: int
    description: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]

# Referral configuration
REFERRAL_CONFIG = {
    "friend_signed_up": 50,      # Credits when friend registers
    "friend_activated": 25,      # Credits when friend becomes active
    "friend_upgraded": 100,      # Credits when friend upgrades tier
    "monthly_bonus": 25,         # Credits for active referred users
    "max_invitations_per_hour": 10,
    "invitation_expiry_days": 30
}

def generate_referral_code() -> str:
    """Generate a unique referral code."""
    return f"WOLFY-{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))}"

def is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_disposable_email(email: str) -> bool:
    """Check if email is from a disposable email service."""
    disposable_domains = [
        '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
        'mailinator.com', 'throwaway.email', 'temp-mail.org'
    ]
    domain = email.split('@')[1].lower()
    return domain in disposable_domains

@router.post("/invite", response_model=InviteResponse)
async def send_invitation(
    invite_request: InviteRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db)
):
    """Send a referral invitation to a friend."""
    
    try:
        logger.info(f"Starting invitation process for email: {invite_request.email}")
        current_user = _get_current_user_from_request(request, db)
        logger.info(f"Current user: {current_user.email} (ID: {current_user.id})")
    except Exception as e:
        logger.error(f"Error in authentication: {e}")
        raise
    
    # Validate email
    if not is_valid_email(invite_request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    if is_disposable_email(invite_request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disposable email addresses are not allowed"
        )
    
    # Check rate limiting
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_invitations = db.query(ReferralInvitation).filter(
        ReferralInvitation.referrer_id == current_user.id,
        ReferralInvitation.created_at >= one_hour_ago
    ).count()
    
    if recent_invitations >= REFERRAL_CONFIG["max_invitations_per_hour"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many invitations sent. Please wait before sending more."
        )
    
    # Check if email already invited by this user
    existing_invitation = db.query(ReferralInvitation).filter(
        ReferralInvitation.referrer_id == current_user.id,
        ReferralInvitation.invited_email == invite_request.email,
        ReferralInvitation.status.in_([ReferralStatus.PENDING, ReferralStatus.SENT, ReferralStatus.OPENED])
    ).first()
    
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already invited this email address"
        )
    
    # Get or create user's referral code
    referral_code_obj = db.query(ReferralCode).filter(
        ReferralCode.user_id == current_user.id
    ).first()
    
    if not referral_code_obj:
        referral_code_obj = ReferralCode(
            user_id=current_user.id,
            code=generate_referral_code()
        )
        db.add(referral_code_obj)
        db.commit()
    
    # Create invitation
    invitation = ReferralInvitation(
        referrer_id=current_user.id,
        invited_email=invite_request.email,
        referral_code=referral_code_obj.code,
        personal_message=invite_request.personal_message,
        status=ReferralStatus.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    
    # No credits for just sending invitation - only when friend signs up
    
    # Send email in background
    background_tasks.add_task(
        send_invitation_email,
        invitation.id,
        invite_request.email,
        current_user.full_name or current_user.email,
        invite_request.personal_message or "",
        referral_code_obj.code
    )
    
    return InviteResponse(
        success=True,
        message="Invitation sent successfully! You'll earn 50 credits when your friend signs up!",
        referral_code=referral_code_obj.code,
        credits_earned=0
    )

@router.get("/my-invitations")
async def get_my_invitations(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get current user's referral invitations."""
    
    current_user = _get_current_user_from_request(request, db)
    
    invitations = db.query(ReferralInvitation).filter(
        ReferralInvitation.referrer_id == current_user.id
    ).order_by(ReferralInvitation.created_at.desc()).all()
    
    return {
        "invitations": [
            {
                "id": inv.id,
                "email": inv.invited_email,
                "status": inv.status.value,
                "credits_earned": inv.credits_earned,
                "created_at": inv.created_at.isoformat(),
                "sent_at": inv.sent_at.isoformat() if inv.sent_at else None,
                "opened_at": inv.opened_at.isoformat() if inv.opened_at else None,
                "signed_up_at": inv.signed_up_at.isoformat() if inv.signed_up_at else None,
                "expires_at": inv.expires_at.isoformat(),
                "personal_message": inv.personal_message
            }
            for inv in invitations
        ]
    }

@router.get("/stats", response_model=ReferralStats)
async def get_referral_stats(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get referral statistics for current user."""
    
    current_user = _get_current_user_from_request(request, db)
    
    # Get all invitations
    invitations = db.query(ReferralInvitation).filter(
        ReferralInvitation.referrer_id == current_user.id
    ).all()
    
    total_invitations = len(invitations)
    successful_signups = len([inv for inv in invitations if inv.status == ReferralStatus.SIGNED_UP])
    conversion_rate = (successful_signups / total_invitations * 100) if total_invitations > 0 else 0
    total_credits_earned = sum(inv.credits_earned for inv in invitations)
    pending_invitations = len([inv for inv in invitations if inv.status in [ReferralStatus.PENDING, ReferralStatus.SENT, ReferralStatus.OPENED]])
    
    # Recent activity (last 10 invitations, sorted by most recent first)
    sorted_invitations = sorted(invitations, key=lambda x: x.created_at, reverse=True)
    recent_activity = [
        {
            "email": inv.invited_email,
            "status": inv.status.value if hasattr(inv.status, 'value') else str(inv.status),
            "created_at": inv.created_at.isoformat(),
            "credits_earned": inv.credits_earned
        }
        for inv in sorted_invitations[:10]
    ]
    
    return ReferralStats(
        total_invitations=total_invitations,
        successful_signups=successful_signups,
        conversion_rate=round(conversion_rate, 2),
        total_credits_earned=total_credits_earned,
        pending_invitations=pending_invitations,
        recent_activity=recent_activity
    )

@router.get("/credits/balance", response_model=CreditBalance)
async def get_credit_balance(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get current user's credit balance."""
    
    current_user = _get_current_user_from_request(request, db)
    
    # Get valid credits (not expired)
    credits = db.query(UserCredit).filter(
        UserCredit.user_id == current_user.id,
        (UserCredit.expires_at.is_(None) | (UserCredit.expires_at > datetime.now(timezone.utc)))
    ).all()
    
    total_credits = sum(credit.amount for credit in credits if credit.amount > 0)
    used_credits = abs(sum(credit.amount for credit in credits if credit.amount < 0))
    available_credits = total_credits - used_credits
    
    # Credits expiring in next 7 days
    seven_days_from_now = datetime.now(timezone.utc) + timedelta(days=7)
    credits_expiring_soon = sum(
        credit.amount for credit in credits
        if credit.expires_at and credit.expires_at <= seven_days_from_now and credit.amount > 0
    )
    
    return CreditBalance(
        total_credits=total_credits,
        available_credits=max(0, available_credits),
        used_credits=used_credits,
        credits_expiring_soon=credits_expiring_soon
    )

@router.get("/credits/history")
async def get_credit_history(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get credit history for current user."""
    
    current_user = _get_current_user_from_request(request, db)
    
    credits = db.query(UserCredit).filter(
        UserCredit.user_id == current_user.id
    ).order_by(UserCredit.created_at.desc()).limit(limit).all()
    
    return {
        "credits": [
            {
                "id": credit.id,
                "credit_type": credit.credit_type.value,
                "amount": credit.amount,
                "description": credit.description,
                "created_at": credit.created_at.isoformat(),
                "expires_at": credit.expires_at.isoformat() if credit.expires_at else None
            }
            for credit in credits
        ]
    }

@router.post("/validate/{referral_code}")
async def validate_referral_code(
    referral_code: str,
    db: Session = Depends(get_db)
):
    """Validate a referral code."""
    
    code_obj = db.query(ReferralCode).filter(
        ReferralCode.code == referral_code,
        ReferralCode.is_active == True
    ).first()
    
    if not code_obj or not code_obj.can_be_used():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired referral code"
        )
    
    # Get referrer info
    referrer = db.query(User).filter(User.id == code_obj.user_id).first()
    
    if not referrer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referrer not found"
        )
    
    return {
        "valid": True,
        "referrer_name": referrer.full_name or referrer.email,
        "referrer_email": referrer.email,
        "code": referral_code
    }

@router.get("/my-code")
async def get_my_referral_code(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get current user's referral code."""
    
    current_user = _get_current_user_from_request(request, db)
    
    referral_code = db.query(ReferralCode).filter(
        ReferralCode.user_id == current_user.id
    ).first()
    
    if not referral_code:
        # Create referral code if it doesn't exist
        referral_code = ReferralCode(
            user_id=current_user.id,
            code=generate_referral_code()
        )
        db.add(referral_code)
        db.commit()
        db.refresh(referral_code)
    
    return {
        "code": referral_code.code,
        "uses_count": referral_code.uses_count,
        "is_active": referral_code.is_active,
        "created_at": referral_code.created_at.isoformat(),
        "last_used_at": referral_code.last_used_at.isoformat() if referral_code.last_used_at else None
    }

# Background task functions
async def send_invitation_email(
    invitation_id: int,
    email: str,
    referrer_name: str,
    personal_message: Optional[str],
    referral_code: str
):
    """Send invitation email in background."""
    try:
        email_service = EmailService()
        await email_service.send_invitation_email(
            to_email=email,
            referrer_name=referrer_name,
            personal_message=personal_message,
            referral_code=referral_code
        )
        
        # Update invitation status to sent
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            invitation = db.query(ReferralInvitation).filter(ReferralInvitation.id == invitation_id).first()
            if invitation:
                invitation.status = ReferralStatus.SENT
                invitation.sent_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to send invitation email: {e}")
        # Update invitation status to failed
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            invitation = db.query(ReferralInvitation).filter(ReferralInvitation.id == invitation_id).first()
            if invitation:
                invitation.status = ReferralStatus.FAILED  # type: ignore
                db.commit()
        finally:
            db.close()

# Helper function to process referral signup
def process_referral_signup(referee_user: User, referral_code: str, db: Session):
    """Process referral signup and award credits."""
    
    # Find the referral code
    code_obj = db.query(ReferralCode).filter(
        ReferralCode.code == referral_code
    ).first()
    
    if not code_obj:
        return False
    
    # Find the invitation
    invitation = db.query(ReferralInvitation).filter(
        ReferralInvitation.referral_code == referral_code,
        ReferralInvitation.invited_email == referee_user.email
    ).first()
    
    if not invitation:
        return False
    
    # Update invitation status
    invitation.status = ReferralStatus.SIGNED_UP
    invitation.signed_up_at = datetime.now(timezone.utc)
    
    # Award credits to referrer
    referrer = db.query(User).filter(User.id == code_obj.user_id).first()
    if referrer:
        referrer.add_credits(
            amount=REFERRAL_CONFIG["friend_signed_up"],
            credit_type=CreditType.REFERRAL.value,
            description=f"Friend {referee_user.email} signed up"
        )
        
        invitation.credits_earned += REFERRAL_CONFIG["friend_signed_up"]
        
        # Create reward record
        reward = ReferralReward(
            referrer_id=referrer.id,
            referee_id=referee_user.id,
            invitation_id=invitation.id,
            reward_type=RewardType.SIGNUP,
            credits_awarded=REFERRAL_CONFIG["friend_signed_up"],
            description=f"Friend {referee_user.email} signed up"
        )
        db.add(reward)
    
    # Award welcome credits to referee
    referee_user.add_credits(
        amount=25,  # Welcome bonus
        credit_type=CreditType.BONUS.value,
        description="Welcome bonus for joining via referral"
    )
    
    # Increment referral code usage
    code_obj.increment_usage()
    
    db.commit()
    return True
