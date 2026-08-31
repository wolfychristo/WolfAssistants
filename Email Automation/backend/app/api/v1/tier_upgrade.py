"""
Manual Tier Upgrade API endpoints

This provides manual tier upgrade functionality for testing and admin purposes.
In production, this would be replaced with proper payment integration.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter()

class TierUpgradeRequest(BaseModel):
    target_tier: str
    subscription_id: Optional[str] = None
    payment_method: str = "manual"  # For testing purposes

class TierUpgradeResponse(BaseModel):
    success: bool
    message: str
    old_tier: str
    new_tier: str
    tier_activated_at: datetime
    tier_expires_at: Optional[datetime]
    new_limits: Dict[str, Any]

@router.post("/upgrade", response_model=TierUpgradeResponse)
def upgrade_tier(
    request: TierUpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upgrade user to a higher tier (for testing/admin purposes)"""
    
    valid_tiers = ["free", "starter", "professional", "enterprise"]
    if request.target_tier not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier. Must be one of: {valid_tiers}"
        )
    
    # Check if user is already on this tier or higher
    tier_hierarchy = {"free": 0, "starter": 1, "professional": 2, "enterprise": 3}
    current_level = tier_hierarchy.get(current_user.pricing_tier, 0)
    target_level = tier_hierarchy.get(request.target_tier, 0)
    
    if target_level <= current_level:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is already on {current_user.pricing_tier} tier or higher"
        )
    
    # Store old tier info
    old_tier = current_user.pricing_tier
    
    # Calculate tier expiration (30 days from now for paid tiers)
    now = datetime.now(timezone.utc)
    if request.target_tier == "free":
        tier_expires_at = None
    else:
        tier_expires_at = now + timedelta(days=30)
    
    # Update user tier
    current_user.pricing_tier = request.target_tier
    current_user.tier_activated_at = now
    current_user.tier_expires_at = tier_expires_at
    current_user.payment_status = "active"
    current_user.subscription_id = request.subscription_id or f"manual_{now.timestamp()}"
    current_user.last_payment_date = now
    current_user.next_payment_date = tier_expires_at
    
    # Save changes
    db.commit()
    db.refresh(current_user)
    
    # Get new tier limits
    new_limits = current_user.get_tier_limits()
    
    return TierUpgradeResponse(
        success=True,
        message=f"Successfully upgraded from {old_tier} to {request.target_tier}",
        old_tier=old_tier,
        new_tier=request.target_tier,
        tier_activated_at=now,
        tier_expires_at=tier_expires_at,
        new_limits=new_limits
    )

@router.post("/downgrade")
def downgrade_tier(
    request: TierUpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Downgrade user to a lower tier (for testing/admin purposes)"""
    
    valid_tiers = ["free", "starter", "professional", "enterprise"]
    if request.target_tier not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier. Must be one of: {valid_tiers}"
        )
    
    # Check if user is already on this tier or lower
    tier_hierarchy = {"free": 0, "starter": 1, "professional": 2, "enterprise": 3}
    current_level = tier_hierarchy.get(current_user.pricing_tier, 0)
    target_level = tier_hierarchy.get(request.target_tier, 0)
    
    if target_level >= current_level:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is already on {current_user.pricing_tier} tier or lower than {request.target_tier}"
        )
    
    # Store old tier info
    old_tier = current_user.pricing_tier
    
    # Calculate tier expiration
    now = datetime.now(timezone.utc)
    if request.target_tier == "free":
        tier_expires_at = None
    else:
        tier_expires_at = now + timedelta(days=30)
    
    # Update user tier
    current_user.pricing_tier = request.target_tier
    current_user.tier_activated_at = now
    current_user.tier_expires_at = tier_expires_at
    current_user.payment_status = "active"
    current_user.subscription_id = request.subscription_id or f"manual_{now.timestamp()}"
    current_user.last_payment_date = now
    current_user.next_payment_date = tier_expires_at
    
    # Save changes
    db.commit()
    db.refresh(current_user)
    
    # Get new tier limits
    new_limits = current_user.get_tier_limits()
    
    return {
        "success": True,
        "message": f"Successfully downgraded from {old_tier} to {request.target_tier}",
        "old_tier": old_tier,
        "new_tier": request.target_tier,
        "tier_activated_at": now,
        "tier_expires_at": tier_expires_at,
        "new_limits": new_limits
    }

@router.post("/reset-to-free")
def reset_to_free_tier(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset user to free tier (for testing purposes)"""
    
    old_tier = current_user.pricing_tier
    now = datetime.now(timezone.utc)
    
    # Reset to free tier
    current_user.pricing_tier = "free"
    current_user.tier_activated_at = now
    current_user.tier_expires_at = None
    current_user.payment_status = "active"
    current_user.subscription_id = None
    current_user.last_payment_date = None
    current_user.next_payment_date = None
    
    # Save changes
    db.commit()
    db.refresh(current_user)
    
    # Get free tier limits
    new_limits = current_user.get_tier_limits()
    
    return {
        "success": True,
        "message": f"Successfully reset from {old_tier} to free tier",
        "old_tier": old_tier,
        "new_tier": "free",
        "tier_activated_at": now,
        "tier_expires_at": None,
        "new_limits": new_limits
    }


def _get_required_tier_for_feature(feature: str) -> str:
    """Get the minimum tier required for a feature"""
    
    feature_tier_mapping = {
        "basic_chat": "free",
        "email_composition": "free", 
        "basic_analytics": "free",
        "email_scheduling": "starter",
        "basic_templates": "starter",
        "advanced_analytics": "professional",
        "custom_templates": "professional",
        "team_collaboration": "professional",
        "api_access": "enterprise",
        "priority_support": "enterprise"
    }
    
    return feature_tier_mapping.get(feature, "enterprise")
