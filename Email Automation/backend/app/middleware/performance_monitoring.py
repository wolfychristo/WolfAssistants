"""
Performance monitoring middleware for tracking endpoint response times.
Helps identify slow endpoints and performance bottlenecks.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import logging
from typing import Dict, List
from collections import defaultdict, deque
from datetime import datetime

logger = logging.getLogger(__name__)

# Store performance metrics
_performance_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))  # Keep last 1000 requests per endpoint


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to track endpoint performance metrics."""
    
    def __init__(self, app, slow_request_threshold: float = 1.0):
        """
        Args:
            app: FastAPI application
            slow_request_threshold: Log warning if request takes longer than this (seconds)
        """
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
    
    async def dispatch(self, request: Request, call_next):
        # Skip monitoring for certain paths
        if self._should_skip_monitoring(request):
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Record error response time
            duration = time.time() - start_time
            self._record_metric(request, duration, error=True)
            raise
        
        # Record response time
        duration = time.time() - start_time
        self._record_metric(request, duration, status_code=response.status_code)
        
        # Add performance header
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        # Log slow requests
        if duration > self.slow_request_threshold:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {duration:.3f}s (threshold: {self.slow_request_threshold}s)"
            )
        
        return response
    
    def _should_skip_monitoring(self, request: Request) -> bool:
        """Skip monitoring for health checks and static files."""
        path = request.url.path
        skip_paths = ["/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"]
        return any(path.startswith(skip) for skip in skip_paths)
    
    def _record_metric(self, request: Request, duration: float, status_code: int = 200, error: bool = False):
        """Record performance metric for an endpoint."""
        endpoint_key = f"{request.method} {request.url.path}"
        
        metric = {
            "timestamp": datetime.utcnow(),
            "duration": duration,
            "status_code": status_code,
            "error": error,
        }
        
        _performance_metrics[endpoint_key].append(metric)


def get_performance_stats() -> Dict[str, Dict]:
    """
    Get performance statistics for all endpoints.
    
    Returns:
        Dictionary with endpoint keys and statistics:
        {
            "GET /api/v1/emails": {
                "count": 100,
                "avg_duration": 0.234,
                "min_duration": 0.012,
                "max_duration": 1.456,
                "p95_duration": 0.567,
                "p99_duration": 0.890,
                "error_count": 2,
                "error_rate": 0.02
            },
            ...
        }
    """
    stats = {}
    
    for endpoint, metrics in _performance_metrics.items():
        if not metrics:
            continue
        
        durations = [m["duration"] for m in metrics]
        errors = [m for m in metrics if m["error"] or m["status_code"] >= 400]
        
        sorted_durations = sorted(durations)
        count = len(durations)
        
        stats[endpoint] = {
            "count": count,
            "avg_duration": sum(durations) / count if count > 0 else 0,
            "min_duration": min(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "p95_duration": sorted_durations[int(count * 0.95)] if count > 0 else 0,
            "p99_duration": sorted_durations[int(count * 0.99)] if count > 0 else 0,
            "error_count": len(errors),
            "error_rate": len(errors) / count if count > 0 else 0,
        }
    
    return stats


def get_slow_endpoints(threshold: float = 1.0, limit: int = 10) -> List[Dict]:
    """
    Get the slowest endpoints.
    
    Args:
        threshold: Minimum average duration to include
        limit: Maximum number of endpoints to return
        
    Returns:
        List of endpoint stats sorted by average duration (slowest first)
    """
    stats = get_performance_stats()
    
    slow_endpoints = [
        {**stats[endpoint], "endpoint": endpoint}
        for endpoint in stats
        if stats[endpoint]["avg_duration"] >= threshold
    ]
    
    slow_endpoints.sort(key=lambda x: x["avg_duration"], reverse=True)
    return slow_endpoints[:limit]


def clear_performance_metrics():
    """Clear all performance metrics (useful for testing)."""
    global _performance_metrics
    _performance_metrics.clear()

