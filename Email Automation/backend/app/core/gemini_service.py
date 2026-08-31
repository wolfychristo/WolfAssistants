from typing import Dict, Any, Optional, Callable
import asyncio
import time
import hashlib
import json
import logging
from datetime import datetime, timedelta
from app.core.gemini_rate_limiter import rate_limiter
from app.core.config import settings
from app.core.gemini_key_manager import key_manager
from app.core.request_queue import request_queue, RequestPriority
import google.generativeai as genai

logger = logging.getLogger(__name__)

class WolfAssistantsService:
    """Centralized service for all WolfAssistants AI interactions with rate limiting and caching."""

    def __init__(self):
        self._response_cache = {}  # Cache for similar requests
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

    def _get_cache_key(self, request_data: Dict[str, Any]) -> str:
        """Generate cache key for request deduplication."""
        # Create normalized request for caching
        normalized = {
            'endpoint': request_data.get('endpoint', ''),
            'prompt_template': request_data.get('prompt_template', ''),
            'context': str(sorted(request_data.get('context', {}).items()))[:500]
        }
        return hashlib.md5(json.dumps(normalized, sort_keys=True).encode()).hexdigest()

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached response is still valid."""
        if cache_key not in self._response_cache:
            return False

        cached_item = self._response_cache[cache_key]
        return datetime.now() - cached_item['timestamp'] < timedelta(seconds=self._cache_ttl)

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if available and valid."""
        if self._is_cache_valid(cache_key):
            return self._response_cache[cache_key]['response']
        return None

    def _cache_response(self, cache_key: str, response: str):
        """Cache a response for future use."""
        self._response_cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now()
        }

        # Clean up old cache entries (keep only last 1000)
        if len(self._response_cache) > 1000:
            # Get the 100 oldest entries to remove
            oldest_keys = sorted(self._response_cache.keys(),
                               key=lambda k: self._response_cache[k]['timestamp'])[:100]
            for key in oldest_keys:
                del self._response_cache[key]

    async def make_request(
        self,
        user_email: str,
        endpoint: str,
        request_type: str,
        prompt_func: Callable,
        context: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        priority: str = 'normal'
    ) -> Dict[str, Any]:
        """Make a rate-limited Gemini API request with caching, queuing, and error handling."""
        
        # Determine request priority
        priority_map = {
            'critical': RequestPriority.CRITICAL,
            'high': RequestPriority.HIGH,
            'normal': RequestPriority.NORMAL,
            'low': RequestPriority.LOW
        }
        request_priority = priority_map.get(priority, RequestPriority.NORMAL)
        
        # For critical/high priority, use queue (optional - can be disabled)
        # Note: Queue is disabled by default for now, can be enabled via config
        use_queue = getattr(settings, 'REQUEST_QUEUE_ENABLED', False)
        if use_queue and request_priority in [RequestPriority.CRITICAL, RequestPriority.HIGH]:
            async def process_request():
                return await self._make_actual_request(
                    user_email, endpoint, request_type, prompt_func, context, use_cache, priority
                )
            
            return await request_queue.process_request()
        else:
            # Normal/low priority: process directly
            return await self._make_actual_request(
                user_email, endpoint, request_type, prompt_func, context, use_cache, priority
            )

    async def _make_actual_request(
        self,
        user_email: str,
        endpoint: str,
        request_type: str,
        prompt_func: Callable,
        context: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        priority: str = 'normal'
    ) -> Dict[str, Any]:
        """Internal method to make the actual API request"""
        
        if context is None:
            context = {}

        api_key = None  # Initialize api_key for error handling

        # Generate cache key for potential use
        request_data = {
            'endpoint': endpoint,
            'request_type': request_type,
            'prompt_template': context.get('prompt_template', ''),
            'context': context
        }
        cache_key = self._get_cache_key(request_data)

        # Check cache first
        if use_cache:
            cached_response = self._get_cached_response(cache_key)

            if cached_response:
                # Record cached usage
                rate_limiter.record_usage(
                    user_email=user_email,
                    endpoint=endpoint,
                    request_type=request_type,
                    success=True,
                    cached_response=True,
                    priority=priority
                )
                return {
                    'success': True,
                    'response': cached_response,
                    'cached': True,
                    'tokens_used': 0
                }

        # Check rate limits
        allowed, rate_limit_info = rate_limiter.check_rate_limit(user_email, endpoint, request_type)

        if not allowed:
            return {
                'success': False,
                'error': rate_limit_info['error'],
                'message': rate_limit_info['message'],
                'retry_after': rate_limit_info['retry_after']
            }

        # Acquire semaphore to limit concurrent requests
        async with self._semaphore:
            start_time = time.time()

            try:
                # Generate prompt using provided function
                prompt = prompt_func(context)

                # Get API key using user-based assignment with fallback
                from app.core.user_api_key_assigner import user_key_assigner
                from app.core.database import SessionLocal
                
                api_key = None
                db = SessionLocal()
                try:
                    # Try user-based key assignment first
                    api_key = user_key_assigner.get_api_key_for_user(user_email, db)
                except Exception as e:
                    logger.warning(f"User-based key assignment failed: {e}, falling back to key manager")
                finally:
                    db.close()
                
                # Fallback to key manager if user-based assignment fails
                if not api_key:
                    api_key = await key_manager.get_next_key()
                
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("gemini_service.py:126", "API key retrieved", {"has_key": bool(api_key), "endpoint": endpoint}, "H3")
                except: pass
                # #endregion
                if not api_key:
                    return {
                        'success': False,
                        'error': 'no_api_key',
                        'message': 'No healthy WolfAssistants AI keys available'
                    }

                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.0-flash")
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("gemini_service.py:137", "before Gemini API call", {"prompt_length": len(prompt)}, "H3")
                except: pass
                # #endregion

                response = model.generate_content(prompt)
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("gemini_service.py:150", "after Gemini API call", {"has_response": bool(response)}, "H3")
                except: pass
                # #endregion
                # Handle response safely - response.text might not exist or raise exception
                try:
                    response_text = response.text if hasattr(response, 'text') and response.text else ""
                except Exception:
                    # If response.text access fails, try alternative methods
                    try:
                        response_text = str(response) if response else ""
                    except:
                        response_text = ""

                response_time = time.time() - start_time

                # Estimate tokens used (more accurate approximation)
                # Gemini typically uses ~4 characters per token for English text
                prompt_tokens = max(len(prompt) // 4, 1)
                response_tokens = max(len(response_text) // 4, 1)
                tokens_used = prompt_tokens + response_tokens

                # Cache the response
                if use_cache and response_text:
                    self._cache_response(cache_key, response_text)

                # Record successful usage
                rate_limiter.record_usage(
                    user_email=user_email,
                    endpoint=endpoint,
                    request_type=request_type,
                    tokens_used=tokens_used,
                    response_time=response_time,
                    success=True,
                    priority=priority
                )
                
                # Record success in key manager
                await key_manager.record_success(api_key, response_time)

                return {
                    'success': True,
                    'response': response_text,
                    'cached': False,
                    'tokens_used': tokens_used,
                    'response_time': response_time
                }

            except Exception as e:
                response_time = time.time() - start_time
                error_message = str(e)
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("gemini_service.py:182", "Gemini API exception", {"error": error_message, "error_type": type(e).__name__, "response_time": response_time}, "H3")
                except: pass
                # #endregion

                # Check if this is a quota exceeded error (429)
                is_quota_error = '429' in error_message or 'quota' in error_message.lower() or 'ResourceExhausted' in str(type(e).__name__)
                
                # Record failed usage
                rate_limiter.record_usage(
                    user_email=user_email,
                    endpoint=endpoint,
                    request_type=request_type,
                    success=False,
                    error_message=error_message,
                    response_time=response_time,
                    priority=priority
                )
                
                # Record failure in key manager (if api_key was set)
                try:
                    if api_key:
                        await key_manager.record_failure(api_key, error_message)
                except NameError:
                    # api_key was not defined, skip recording
                    pass

                # Return appropriate error type
                if is_quota_error:
                    return {
                        'success': False,
                        'error': 'quota_exceeded',
                        'message': 'Gemini API quota exceeded. Please try again later or upgrade your API plan.',
                        'response_time': response_time,
                        'quota_exceeded': True
                    }
                else:
                    return {
                        'success': False,
                        'error': 'api_error',
                        'message': f'WolfAssistants AI error: {error_message}',
                        'response_time': response_time
                    }

    def get_usage_stats(self, user_email: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """Get usage statistics."""
        return rate_limiter.get_usage_stats(user_email, hours)

    def clear_cache(self):
        """Clear response cache."""
        self._response_cache.clear()
        rate_limiter.clear_cache()

# Global service instance
wolf_assistants_service = WolfAssistantsService()
# Alias for backward compatibility
wolfy_service = wolf_assistants_service
