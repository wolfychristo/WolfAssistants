from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.core.database import get_db, SessionLocal
from app.core.gemini_service import wolf_assistants_service
from app.core.gemini_rate_limiter import rate_limiter
from app.models.gemini_usage import WolfAssistantsUsage
from sqlalchemy import func

router = APIRouter()

def _get_owner_from_request(request: Request) -> str:
    """Extract user email from JWT token."""
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(' ', 1)[1]
    try:
        from jose import jwt
        payload = jwt.get_unverified_claims(token)
        email = payload.get('sub')
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token format")

@router.get("/usage")
def get_gemini_usage(
    request: Request,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get Gemini API usage statistics for the authenticated user."""
    owner = _get_owner_from_request(request)

    # Get usage stats for this user
    user_stats = wolf_assistants_service.get_usage_stats(owner, hours)

    # Get global usage stats
    global_stats = wolf_assistants_service.get_usage_stats(hours=hours)

    # Calculate remaining quotas
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Get today's usage from database
    daily_user_usage = db.query(func.count(WolfAssistantsUsage.id)).filter(
        WolfAssistantsUsage.user_email == owner,
        WolfAssistantsUsage.timestamp >= day_start
    ).scalar() or 0

    daily_global_usage = db.query(func.count(WolfAssistantsUsage.id)).filter(
        WolfAssistantsUsage.timestamp >= day_start
    ).scalar() or 0

    # Gemini free tier limits
    DAILY_LIMIT = 1000
    USER_DAILY_LIMIT = 100

    return {
        'user_stats': user_stats,
        'global_stats': global_stats,
        'quotas': {
            'user_daily_used': daily_user_usage,
            'user_daily_limit': USER_DAILY_LIMIT,
            'user_daily_remaining': max(0, USER_DAILY_LIMIT - daily_user_usage),
            'global_daily_used': daily_global_usage,
            'global_daily_limit': DAILY_LIMIT,
            'global_daily_remaining': max(0, DAILY_LIMIT - daily_global_usage)
        },
        'limits_info': {
            'gemini_free_tier': {
                'requests_per_minute': 60,
                'requests_per_day': 1000,
                'note': 'Free tier limits apply globally across all users'
            },
            'user_limits': {
                'requests_per_minute': 20,
                'requests_per_day': 100,
                'note': 'Conservative limits to prevent individual user abuse'
            }
        },
        'timestamp': now.isoformat()
    }

@router.get("/usage/detailed")
def get_detailed_usage(
    request: Request,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get detailed breakdown of Gemini API usage by endpoint and time."""
    owner = _get_owner_from_request(request)
    now = datetime.now()
    since = now - timedelta(hours=hours)

    # Get usage breakdown by endpoint
    endpoint_stats = db.query(
        WolfAssistantsUsage.endpoint,
        func.count(WolfAssistantsUsage.id).label('total_requests'),
        func.avg(WolfAssistantsUsage.response_time).label('avg_response_time'),
        func.sum(func.case((WolfAssistantsUsage.success == True, 1), else_=0)).label('successful_requests'),
        func.sum(WolfAssistantsUsage.tokens_used).label('total_tokens')
    ).filter(
        WolfAssistantsUsage.user_email == owner,
        WolfAssistantsUsage.timestamp >= since
    ).group_by(WolfAssistantsUsage.endpoint).all()

    # Get hourly usage pattern
    hourly_usage = db.query(
        func.strftime('%Y-%m-%d %H:00:00', WolfAssistantsUsage.timestamp).label('hour'),
        func.count(WolfAssistantsUsage.id).label('requests')
    ).filter(
        WolfAssistantsUsage.user_email == owner,
        WolfAssistantsUsage.timestamp >= since
    ).group_by(
        func.strftime('%Y-%m-%d %H', WolfAssistantsUsage.timestamp)
    ).order_by(
        func.strftime('%Y-%m-%d %H', WolfAssistantsUsage.timestamp)
    ).all()

    # Get error breakdown
    error_stats = db.query(
        WolfAssistantsUsage.endpoint,
        WolfAssistantsUsage.error_message,
        func.count(WolfAssistantsUsage.id).label('error_count')
    ).filter(
        WolfAssistantsUsage.user_email == owner,
        WolfAssistantsUsage.timestamp >= since,
        WolfAssistantsUsage.success == False
    ).group_by(
        WolfAssistantsUsage.endpoint,
        WolfAssistantsUsage.error_message
    ).all()

    return {
        'endpoint_breakdown': [
            {
                'endpoint': stat.endpoint,
                'total_requests': stat.total_requests,
                'successful_requests': stat.successful_requests,
                'success_rate': stat.successful_requests / stat.total_requests if stat.total_requests > 0 else 0,
                'avg_response_time': float(stat.avg_response_time or 0),
                'total_tokens': stat.total_tokens or 0
            }
            for stat in endpoint_stats
        ],
        'hourly_usage': [
            {
                'hour': stat.hour,
                'requests': stat.requests
            }
            for stat in hourly_usage
        ],
        'error_breakdown': [
            {
                'endpoint': stat.endpoint,
                'error_message': stat.error_message,
                'error_count': stat.error_count
            }
            for stat in error_stats
        ],
        'period': f'Last {hours} hours'
    }

@router.post("/cache/clear")
def clear_gemini_cache(request: Request):
    """Clear Gemini response cache (admin function)."""
    owner = _get_owner_from_request(request)

    # TODO: Add admin role check here
    # For now, allowing any authenticated user to clear their own cache

    wolf_assistants_service.clear_cache()

    return {
        'success': True,
        'message': 'Gemini cache cleared successfully',
        'timestamp': datetime.now().isoformat()
    }

@router.get("/health")
def get_gemini_health():
    """Get Gemini API health status."""
    # Get global usage stats for last hour
    stats = wolf_assistants_service.get_usage_stats(hours=1)

    # Check if we're approaching limits
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Get today's usage
    db = SessionLocal()
    try:
        daily_global_usage = db.query(func.count(WolfAssistantsUsage.id)).filter(
            WolfAssistantsUsage.timestamp >= day_start
        ).scalar() or 0
    finally:
        db.close()

    DAILY_LIMIT = 1000
    usage_percentage = (daily_global_usage / DAILY_LIMIT) * 100

    health_status = 'healthy'
    if usage_percentage > 90:
        health_status = 'critical'
    elif usage_percentage > 75:
        health_status = 'warning'
    elif usage_percentage > 50:
        health_status = 'caution'

    return {
        'status': health_status,
        'daily_usage': daily_global_usage,
        'daily_limit': DAILY_LIMIT,
        'usage_percentage': usage_percentage,
        'remaining_requests': max(0, DAILY_LIMIT - daily_global_usage),
        'recent_stats': stats,
        'last_updated': now.isoformat()
    }
