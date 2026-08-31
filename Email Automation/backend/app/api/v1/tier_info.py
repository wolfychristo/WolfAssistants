"""
Tier Information API endpoints

Provides information about user tiers, limits, and features.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.middleware.tier_enforcement import get_tier_limits, check_user_tier_access

router = APIRouter()

@router.get("/my-tier")
def get_my_tier_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's tier information and limits"""
    
    tier_info = {
        "tier": current_user.pricing_tier,
        "is_active": current_user.is_tier_active(),
        "payment_status": current_user.payment_status,
        "tier_activated_at": current_user.tier_activated_at,
        "tier_expires_at": current_user.tier_expires_at,
        "last_payment_date": current_user.last_payment_date,
        "next_payment_date": current_user.next_payment_date,
        "limits": current_user.get_tier_limits(),
        "features": get_tier_limits(current_user.pricing_tier).get("features", [])
    }
    
    return tier_info

@router.get("/tier-limits/{tier}")
def get_tier_limits_info(tier: str):
    """Get limits and features for a specific tier"""
    
    valid_tiers = ["free", "starter", "professional", "enterprise"]
    if tier not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier. Must be one of: {valid_tiers}"
        )
    
    limits = get_tier_limits(tier)
    
    return {
        "tier": tier,
        "limits": limits,
        "features": limits.get("features", [])
    }

@router.get("/all-tiers")
def get_all_tiers():
    """Get information about all available tiers"""
    
    tiers = ["free", "starter", "professional", "enterprise"]
    
    all_tier_info = {}
    for tier in tiers:
        limits = get_tier_limits(tier)
        all_tier_info[tier] = {
            "limits": limits,
            "features": limits.get("features", [])
        }
    
    return all_tier_info

@router.get("/check-feature/{feature}")
def check_feature_access(
    feature: str,
    current_user: User = Depends(get_current_user)
):
    """Check if current user can access a specific feature"""
    
    can_access = check_user_tier_access(current_user, feature)
    
    return {
        "feature": feature,
        "can_access": can_access,
        "user_tier": current_user.pricing_tier,
        "required_tier": _get_required_tier_for_feature(feature)
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
