from typing import Dict, Any, Optional, List, Tuple
import hashlib
import json
import asyncio
from datetime import datetime, timedelta
from collections import OrderedDict

class GeminiResponseCache:
    """LRU cache for Gemini API responses to reduce redundant calls."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()  # LRU cache
        self._lock = asyncio.Lock()

    def _generate_cache_key(self, request_data: Dict[str, Any]) -> str:
        """Generate a cache key from request data."""
        # Create normalized request for caching
        normalized = {
            'endpoint': request_data.get('endpoint', ''),
            'request_type': request_data.get('request_type', ''),
            'prompt_template': request_data.get('prompt_template', ''),
            'context_keys': sorted(request_data.get('context', {}).keys()),
            'context_hash': hashlib.md5(
                json.dumps(request_data.get('context', {}), sort_keys=True).encode()
            ).hexdigest()[:16]  # First 16 chars of context hash
        }
        return hashlib.md5(json.dumps(normalized, sort_keys=True).encode()).hexdigest()

    def _is_expired(self, timestamp: datetime) -> bool:
        """Check if a cache entry has expired."""
        return datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds)

    async def get(self, request_data: Dict[str, Any]) -> Optional[str]:
        """Get a cached response if available."""
        async with self._lock:
            cache_key = self._generate_cache_key(request_data)

            if cache_key in self._cache:
                entry = self._cache[cache_key]

                # Check if expired
                if self._is_expired(entry['timestamp']):
                    del self._cache[cache_key]
                    return None

                # Move to end (most recently used)
                self._cache.move_to_end(cache_key)
                return entry['response']

            return None

    async def set(self, request_data: Dict[str, Any], response: str, metadata: Optional[Dict[str, Any]] = None):
        """Cache a response."""
        async with self._lock:
            cache_key = self._generate_cache_key(request_data)

            # Clean up expired entries and enforce max size
            self._cleanup()

            # Add new entry
            self._cache[cache_key] = {
                'response': response,
                'timestamp': datetime.now(),
                'metadata': metadata or {}
            }

            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)

    def _cleanup(self):
        """Clean up expired entries and enforce max size."""
        now = datetime.now()

        # Remove expired entries
        expired_keys = []
        for key, entry in self._cache.items():
            if self._is_expired(entry['timestamp']):
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        # If still over max size, remove oldest entries
        while len(self._cache) > self.max_size:
            oldest_key, _ = self._cache.popitem(last=False)
            # oldest_key is already removed by popitem

    async def clear(self):
        """Clear all cached entries."""
        async with self._lock:
            self._cache.clear()

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            total_entries = len(self._cache)
            now = datetime.now()

            expired_count = sum(1 for entry in self._cache.values() if self._is_expired(entry['timestamp']))

            # Calculate cache hit ratio (simplified - would need more tracking in production)
            hit_ratio = 0.0  # Would track hits/misses in production

            return {
                'total_entries': total_entries,
                'max_size': self.max_size,
                'ttl_seconds': self.ttl_seconds,
                'expired_entries': expired_count,
                'active_entries': total_entries - expired_count,
                'utilization_percent': (total_entries / self.max_size) * 100 if self.max_size > 0 else 0,
                'hit_ratio_estimate': hit_ratio
            }

    async def get_similar_responses(self, request_data: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """Get similar cached responses for fallback scenarios."""
        async with self._lock:
            cache_key = self._generate_cache_key(request_data)

            # Get responses with similar context hash
            similar_responses = []
            base_context_hash = hashlib.md5(
                json.dumps(request_data.get('context', {}), sort_keys=True).encode()
            ).hexdigest()[:8]  # First 8 chars

            for key, entry in self._cache.items():
                if key != cache_key and not self._is_expired(entry['timestamp']):
                    # Simple similarity check based on context hash prefix
                    if base_context_hash in key[:16]:  # Check if context hash prefix matches
                        similar_responses.append({
                            'response': entry['response'],
                            'metadata': entry.get('metadata', {}),
                            'timestamp': entry['timestamp']
                        })

            # Sort by timestamp (most recent first) and limit results
            similar_responses.sort(key=lambda x: x['timestamp'], reverse=True)
            return similar_responses[:limit]

# Global cache instance
response_cache = GeminiResponseCache()
