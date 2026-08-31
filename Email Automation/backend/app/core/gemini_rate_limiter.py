from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import hashlib
import json
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.gemini_usage import WolfyUsage

class WolfyRateLimiter:
    """Comprehensive rate limiting for Wolfy AI API calls."""

    # Wolfy AI Free Tier Limits (60/min, 1000/day)
    GLOBAL_LIMITS = {
        'minute': 60,
        'day': 1000
    }

    # Per-user limits (more conservative to prevent abuse)
    USER_LIMITS = {
        'minute': 20,
        'day': 100
    }

    # Endpoint-specific limits for priority management
    ENDPOINT_LIMITS = {
        'email_generation': {'user_minute': 10, 'priority': 'high'},
        'chat_response': {'user_minute': 15, 'priority': 'high'},
        'intent_parsing': {'user_minute': 30, 'priority': 'normal'},
        'web_research': {'user_minute': 5, 'priority': 'low'}
    }

    def __init__(self):
        self._cache = {}  # Simple in-memory cache for rate limiting
        self._response_cache = {}  # Cache for similar requests

    def _get_cache_key(self, user_email: str, period: str) -> str:
        """Generate cache key for rate limiting."""
        now = datetime.now()
        if period == 'minute':
            key = f"{user_email}:{now.minute}:{now.hour}:{now.day}"
        else:  # day
            key = f"{user_email}:{now.day}:{now.month}:{now.year}"
        return key

    def _get_request_hash(self, request_data: Dict[str, Any]) -> str:
        """Generate hash for request deduplication."""
        # Create a normalized version of the request for caching
        normalized = {
            'endpoint': request_data.get('endpoint', ''),
            'request_type': request_data.get('request_type', ''),
            'message': request_data.get('message', '')[:200],  # First 200 chars
            'context': str(sorted(request_data.get('context', {}).items()))[:100]
        }
        return hashlib.md5(json.dumps(normalized, sort_keys=True).encode()).hexdigest()

    def check_rate_limit(self, user_email: str, endpoint: str, request_type: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limits."""
        now = datetime.now()
        request_data = {
            'endpoint': endpoint,
            'request_type': request_type,
            'user_email': user_email
        }

        # Check endpoint-specific limits first
        endpoint_config = self.ENDPOINT_LIMITS.get(endpoint, {'user_minute': 10, 'priority': 'normal'})
        user_minute_limit = endpoint_config.get('user_minute', 10)

        # Check per-user minute limit for this endpoint
        user_minute_key = f"endpoint:{user_email}:{endpoint}:{now.minute}"
        user_minute_count = self._cache.get(user_minute_key, 0)

        if user_minute_count >= user_minute_limit:
            return False, {
                'error': 'endpoint_rate_limit',
                'message': f'Too many requests for {endpoint}. Limit: {user_minute_limit}/minute',
                'retry_after': 60
            }

        # Check global user limits
        for period, limit in self.USER_LIMITS.items():
            cache_key = self._get_cache_key(user_email, period)
            count = self._cache.get(cache_key, 0)

            if count >= limit:
                return False, {
                    'error': 'user_rate_limit',
                    'message': f'User rate limit exceeded. Limit: {limit}/{period}',
                    'retry_after': 60 if period == 'minute' else 86400
                }

        # Check global limits for each period
        for period, limit in self.GLOBAL_LIMITS.items():
            global_key = f"global:{period}"
            global_count = self._cache.get(global_key, 0)

            if global_count >= limit:
                return False, {
                    'error': 'global_rate_limit',
                    'message': f'Global rate limit exceeded. Limit: {limit}/{period}',
                    'retry_after': 60 if period == 'minute' else 86400
                }

        return True, {'priority': endpoint_config.get('priority', 'normal')}

    def record_usage(self, user_email: str, endpoint: str, request_type: str,
                    tokens_used: int = 0, response_time: float = 0.0,
                    success: bool = True, error_message: Optional[str] = None,
                    cached_response: bool = False, priority: str = 'normal'):
        """Record API usage for monitoring and rate limiting."""
        now = datetime.now()

        # Update cache for rate limiting
        for period in ['minute', 'day']:
            cache_key = self._get_cache_key(user_email, period)
            self._cache[cache_key] = self._cache.get(cache_key, 0) + 1

            # Update global count
            global_key = f"global:{period}"
            self._cache[global_key] = self._cache.get(global_key, 0) + 1

        # Update endpoint-specific cache
        endpoint_key = f"endpoint:{user_email}:{endpoint}:{now.minute}"
        self._cache[endpoint_key] = self._cache.get(endpoint_key, 0) + 1

        # Save to database for persistent tracking
        db = SessionLocal()
        try:
            request_data = {
                'endpoint': endpoint,
                'request_type': request_type,
                'user_email': user_email
            }
            request_hash = self._get_request_hash(request_data)

            usage_record = WolfyUsage(
                user_email=user_email,
                endpoint=endpoint,
                request_type=request_type,
                tokens_used=tokens_used,
                response_time=response_time,
                success=success,
                error_message=error_message,
                timestamp=now,
                request_hash=request_hash,
                cached_response=cached_response,
                priority=priority
            )

            db.add(usage_record)
            db.commit()
        except Exception as e:
            db.rollback()
            pass
        finally:
            db.close()

    def get_usage_stats(self, user_email: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """Get usage statistics for monitoring."""
        db = SessionLocal()
        try:
            now = datetime.now()
            since = now - timedelta(hours=hours)

            query = db.query(WolfyUsage).filter(WolfyUsage.timestamp >= since)

            if user_email:
                query = query.filter(WolfyUsage.user_email == user_email)

            total_requests = query.count()
            successful_requests = query.filter(WolfyUsage.success == True).count()
            failed_requests = query.filter(WolfyUsage.success == False).count()

            # Calculate average response time
            avg_response_time = db.query(func.avg(WolfyUsage.response_time)).filter(
                WolfyUsage.timestamp >= since,
                WolfyUsage.success == True
            ).scalar() or 0.0

            # Get daily breakdown
            daily_usage = {}
            if hours >= 24:  # Only create daily breakdown if period is 24+ hours
                for i in range(hours // 24 + 1):
                    day_start = now - timedelta(days=i)
                    day_end = day_start + timedelta(days=1)

                    day_requests = query.filter(
                        WolfyUsage.timestamp >= day_start,
                        WolfyUsage.timestamp < day_end
                    ).count()

                    daily_usage[day_start.strftime('%Y-%m-%d')] = day_requests
            else:
                # For periods less than 24 hours, show hourly breakdown
                for i in range(hours + 1):
                    hour_start = now - timedelta(hours=i)
                    hour_end = hour_start + timedelta(hours=1)

                    hour_requests = query.filter(
                        WolfyUsage.timestamp >= hour_start,
                        WolfyUsage.timestamp < hour_end
                    ).count()

                    daily_usage[hour_start.strftime('%Y-%m-%d %H:00')] = hour_requests

            return {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
                'average_response_time': avg_response_time,
                'daily_usage': daily_usage,
                'period_hours': hours
            }
        finally:
            db.close()

    def clear_cache(self):
        """Clear rate limiting cache (for testing/admin purposes)."""
        self._cache.clear()

# Global instance
rate_limiter = WolfyRateLimiter()
