"""
Tier Enforcement Middleware

This middleware enforces pricing tier limits and access controls
based on user subscription status and tier limits.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_db, SessionLocal
from app.models.user import User
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

class TierEnforcementMiddleware:
    """Middleware to enforce pricing tier limits and access controls"""
    
    def __init__(self, app):
        self.app = app
        
        # Define tier limits for different features
        self.tier_limits = {
            "free": {
                "emails_per_month": 100,
                "ai_requests_per_day": 20,
                "team_members": 1,
                "storage_gb": 1,
                "features": ["basic_chat", "email_composition", "basic_analytics"]
            },
            "starter": {
                "emails_per_month": 1000,
                "ai_requests_per_day": 100,
                "team_members": 3,
                "storage_gb": 10,
                "features": ["basic_chat", "email_composition", "basic_analytics", 
                           "email_scheduling", "basic_templates"]
            },
            "professional": {
                "emails_per_month": 10000,
                "ai_requests_per_day": 500,
                "team_members": 10,
                "storage_gb": 100,
                "features": ["basic_chat", "email_composition", "basic_analytics", 
                           "email_scheduling", "basic_templates", "advanced_analytics", 
                           "custom_templates", "team_collaboration"]
            },
            "enterprise": {
                "emails_per_month": 100000,
                "ai_requests_per_day": 2000,
                "team_members": -1,  # Unlimited
                "storage_gb": 1000,
                "features": ["basic_chat", "email_composition", "basic_analytics", 
                           "email_scheduling", "basic_templates", "advanced_analytics", 
                           "custom_templates", "team_collaboration", "api_access", 
                           "priority_support"]
            }
        }
        
        # Define protected endpoints and their required features
        self.protected_endpoints = {
            "/api/v1/wolfy/chat": ["basic_chat"],
            "/api/v1/email/compose": ["email_composition"],
            "/api/v1/email/schedule": ["email_scheduling"],
            "/api/v1/templates": ["basic_templates", "custom_templates"],
            "/api/v1/analytics": ["basic_analytics", "advanced_analytics"],
            "/api/v1/team": ["team_collaboration"],
            "/api/v1/api-keys": ["api_access"]
        }
    
    async def __call__(self, request: Request, call_next):
        """Main middleware function"""
        
        # Skip tier enforcement for certain paths
        if self._should_skip_tier_check(request):
            return await call_next(request)
        
        # Get user from request (if authenticated)
        user = await self._get_user_from_request(request)
        
        if not user:
            # Allow unauthenticated requests to pass through
            return await call_next(request)
        
        # Check if user's tier is active
        if not self._is_tier_active(user):
            return self._create_tier_inactive_response(user)
        
        # Check feature access for protected endpoints
        if not self._check_feature_access(request, user):
            return self._create_feature_restricted_response(user, request)
        
        # Check usage limits
        limit_check = await self._check_usage_limits(request, user)
        if not limit_check["allowed"]:
            return self._create_limit_exceeded_response(user, limit_check)
        
        # Continue to the next middleware/handler
        response = await call_next(request)
        
        # Track usage after successful request
        await self._track_usage(request, user)
        
        return response
    
    def _should_skip_tier_check(self, request: Request) -> bool:
        """Check if tier enforcement should be skipped for this request"""
        skip_paths = [
            "/docs",
            "/openapi.json",
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/verify-email",
            "/api/v1/pricing",
            "/api/v1/health"
        ]
        
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    async def _get_user_from_request(self, request: Request) -> Optional[User]:
        """Extract user from request if authenticated"""
        try:
            # Try to get user from authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            # Create credentials object
            token = auth_header.split(" ")[1]
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            
            # Get database session
            db = SessionLocal()
            
            try:
                # Get current user (this will validate the token)
                user = await get_current_user(credentials, db)
                return user
            finally:
                db.close()
            
        except Exception as e:
            logger.debug(f"Could not extract user from request: {e}")
            return None
    
    def _is_tier_active(self, user: User) -> bool:
        """Check if user's current tier is active"""
        if user.pricing_tier == "free":
            return True
        
        # Check if tier has expired
        if user.tier_expires_at and datetime.now(timezone.utc) > user.tier_expires_at:
            return False
        
        # Check if payment is active
        if user.payment_status not in ["active", "trialing"]:
            return False
        
        return True
    
    def _check_feature_access(self, request: Request, user: User) -> bool:
        """Check if user can access the requested feature"""
        path = request.url.path
        
        # Find matching protected endpoint
        required_features = None
        for endpoint, features in self.protected_endpoints.items():
            if path.startswith(endpoint):
                required_features = features
                break
        
        if not required_features:
            return True  # No restrictions for this endpoint
        
        # Check if user's tier supports any of the required features
        user_tier = user.pricing_tier
        user_features = self.tier_limits.get(user_tier, {}).get("features", [])
        
        return any(feature in user_features for feature in required_features)
    
    async def _check_usage_limits(self, request: Request, user: User) -> Dict[str, Any]:
        """Check if user has exceeded their usage limits"""
        user_tier = user.pricing_tier
        limits = self.tier_limits.get(user_tier, self.tier_limits["free"])
        
        # For now, we'll implement basic checks
        # In a full implementation, you'd query actual usage from the database
        
        return {
            "allowed": True,
            "limits": limits,
            "current_usage": {
                "emails_this_month": 0,  # Would be calculated from database
                "ai_requests_today": 0,  # Would be calculated from database
            }
        }
    
    def _create_tier_inactive_response(self, user: User) -> JSONResponse:
        """Create response for inactive tier"""
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "Tier Inactive",
                "message": f"Your {user.pricing_tier} tier is not active. Please check your subscription status.",
                "tier": user.pricing_tier,
                "payment_status": user.payment_status,
                "upgrade_url": "/pricing"
            }
        )
    
    def _create_feature_restricted_response(self, user: User, request: Request) -> JSONResponse:
        """Create response for restricted feature access"""
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "Feature Restricted",
                "message": f"This feature is not available in your {user.pricing_tier} tier.",
                "tier": user.pricing_tier,
                "required_tier": self._get_required_tier_for_feature(request),
                "upgrade_url": "/pricing"
            }
        )
    
    def _create_limit_exceeded_response(self, user: User, limit_check: Dict[str, Any]) -> JSONResponse:
        """Create response for exceeded usage limits"""
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Usage Limit Exceeded",
                "message": "You have exceeded your usage limits for this tier.",
                "tier": user.pricing_tier,
                "limits": limit_check["limits"],
                "current_usage": limit_check["current_usage"],
                "upgrade_url": "/pricing"
            }
        )
    
    def _get_required_tier_for_feature(self, request: Request) -> str:
        """Get the minimum tier required for the requested feature"""
        # This would be implemented based on your feature requirements
        return "starter"
    
    async def _track_usage(self, request: Request, user: User):
        """Track usage for billing and limit enforcement"""
        # This would implement actual usage tracking
        # For now, it's a placeholder
        pass

def get_tier_limits(user_tier: str) -> Dict[str, Any]:
    """Get tier limits for a specific tier"""
    limits = {
        "free": {
            "emails_per_month": 100,
            "ai_requests_per_day": 20,
            "team_members": 1,
            "storage_gb": 1,
            "features": ["basic_chat", "email_composition", "basic_analytics"]
        },
        "starter": {
            "emails_per_month": 1000,
            "ai_requests_per_day": 100,
            "team_members": 3,
            "storage_gb": 10,
            "features": ["basic_chat", "email_composition", "basic_analytics", 
                       "email_scheduling", "basic_templates"]
        },
        "professional": {
            "emails_per_month": 10000,
            "ai_requests_per_day": 500,
            "team_members": 10,
            "storage_gb": 100,
            "features": ["basic_chat", "email_composition", "basic_analytics", 
                       "email_scheduling", "basic_templates", "advanced_analytics", 
                       "custom_templates", "team_collaboration"]
        },
        "enterprise": {
            "emails_per_month": 100000,
            "ai_requests_per_day": 2000,
            "team_members": -1,  # Unlimited
            "storage_gb": 1000,
            "features": ["basic_chat", "email_composition", "basic_analytics", 
                       "email_scheduling", "basic_templates", "advanced_analytics", 
                       "custom_templates", "team_collaboration", "api_access", 
                       "priority_support"]
        }
    }
    
    return limits.get(user_tier, limits["free"])

def check_user_tier_access(user: User, feature: str) -> bool:
    """Check if user can access a specific feature"""
    if not user.is_tier_active() or not user.is_payment_active():
        return False
    
    return user.can_access_feature(feature)
