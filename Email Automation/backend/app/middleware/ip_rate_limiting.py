"""
IP-based rate limiting middleware for WolfAssistants
Protects against DDoS and brute force attacks
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse
import time
import logging
from typing import Dict, List, Tuple
from collections import defaultdict, deque
import asyncio

# Configure rate limiting logger
rate_limit_logger = logging.getLogger("rate_limit")

class IPRateLimiter:
    """Advanced IP-based rate limiter with sliding window"""
    
    def __init__(self):
        # Store requests per IP: {ip: deque of timestamps}
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
        # Store blocked IPs: {ip: (blocked_until, violation_count)}
        self.blocked_ips: Dict[str, Tuple[float, int]] = {}
        # Cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        # Don't start the task during module import
        # It will be started when the application starts
        self._cleanup_task = None
    
    async def _cleanup_loop(self):
        """Background cleanup of old entries"""
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                await self._cleanup_expired_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                rate_limit_logger.error(f"Rate limiter cleanup error: {e}")
    
    async def _cleanup_expired_entries(self):
        """Remove expired entries to prevent memory leaks"""
        current_time = time.time()
        
        # Clean up old requests
        for ip in list(self.requests.keys()):
            requests = self.requests[ip]
            # Remove requests older than 1 hour
            while requests and current_time - requests[0] > 3600:
                requests.popleft()
            
            # Remove empty entries
            if not requests:
                del self.requests[ip]
        
        # Clean up expired blocks
        for ip in list(self.blocked_ips.keys()):
            blocked_until, _ = self.blocked_ips[ip]
            if current_time > blocked_until:
                del self.blocked_ips[ip]
    
    def is_rate_limited(self, ip: str, limit: int, window: int) -> Tuple[bool, str]:
        """
        Check if IP is rate limited
        Returns: (is_limited, reason)
        """
        current_time = time.time()
        
        # Check if IP is currently blocked
        if ip in self.blocked_ips:
            blocked_until, violation_count = self.blocked_ips[ip]
            if current_time < blocked_until:
                remaining_time = int(blocked_until - current_time)
                return True, f"IP blocked for {remaining_time} seconds due to {violation_count} violations"
            else:
                # Block expired, remove it
                del self.blocked_ips[ip]
        
        # Get or create request history for this IP
        requests = self.requests[ip]
        
        # Remove old requests outside the window
        while requests and current_time - requests[0] > window:
            requests.popleft()
        
        # Check if limit exceeded
        if len(requests) >= limit:
            # Increment violation count
            violation_count = self.blocked_ips.get(ip, (0, 0))[1] + 1
            
            # Calculate block duration (exponential backoff)
            block_duration = min(300, 60 * (2 ** min(violation_count - 1, 4)))  # Max 5 minutes
            
            # Block the IP
            self.blocked_ips[ip] = (current_time + block_duration, violation_count)
            
            rate_limit_logger.warning(f"IP {ip} rate limited: {len(requests)} requests in {window}s (violation #{violation_count})")
            return True, f"Rate limit exceeded: {len(requests)} requests in {window} seconds. Blocked for {block_duration} seconds."
        
        # Add current request
        requests.append(current_time)
        return False, ""
    
    @property
    def ip_stats(self) -> Dict[str, Dict]:
        """Get statistics for all IPs"""
        current_time = time.time()
        stats = {}
        
        for ip, requests in self.requests.items():
            # Count requests in last minute, 5 minutes, and hour
            last_minute = sum(1 for req_time in requests if current_time - req_time <= 60)
            last_5_minutes = sum(1 for req_time in requests if current_time - req_time <= 300)
            last_hour = len(requests)
            
            is_blocked = ip in self.blocked_ips
            blocked_until = None
            violation_count = 0
            
            if is_blocked:
                blocked_until, violation_count = self.blocked_ips[ip]
            
            stats[ip] = {
                "ip": ip,
                "request_count": last_hour,
                "last_minute": last_minute,
                "last_5_minutes": last_5_minutes,
                "last_hour": last_hour,
                "is_blocked": is_blocked,
                "blocked_until": blocked_until,
                "violation_count": violation_count
            }
        
        return stats
    
    def get_ip_stats(self, ip: str) -> Dict:
        """Get statistics for a specific IP"""
        current_time = time.time()
        requests = self.requests.get(ip, deque())
        
        # Count requests in last minute, 5 minutes, and hour
        last_minute = sum(1 for req_time in requests if current_time - req_time <= 60)
        last_5_minutes = sum(1 for req_time in requests if current_time - req_time <= 300)
        last_hour = len(requests)
        
        is_blocked = ip in self.blocked_ips
        blocked_until = None
        violation_count = 0
        
        if is_blocked:
            blocked_until, violation_count = self.blocked_ips[ip]
        
        return {
            "ip": ip,
            "last_minute": last_minute,
            "last_5_minutes": last_5_minutes,
            "last_hour": last_hour,
            "is_blocked": is_blocked,
            "blocked_until": blocked_until,
            "violation_count": violation_count
        }

# Global rate limiter instance
ip_rate_limiter = IPRateLimiter()

class IPRateLimitMiddleware(BaseHTTPMiddleware):
    """IP-based rate limiting middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        # Different limits for different endpoint types
        self.limits = {
            "auth": (20, 300),      # 20 requests per 5 minutes
            "api": (200, 300),      # 200 requests per 5 minutes
            "email_settings": (50, 60),  # 50 requests per minute for email settings
            "otp": (10, 300),       # 10 requests per 5 minutes
            "default": (100, 300)   # 100 requests per 5 minutes
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> StarletteResponse:
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Skip rate limiting for localhost in development
        if client_ip in ["127.0.0.1", "::1", "localhost", "unknown"]:
            response = await call_next(request)
            return response
        
        # Determine endpoint type and limits
        endpoint_type = self._get_endpoint_type(request)
        limit, window = self.limits.get(endpoint_type, self.limits["default"])
        
        # Check rate limit
        is_limited, reason = ip_rate_limiter.is_rate_limited(client_ip, limit, window)
        
        if is_limited:
            rate_limit_logger.warning(f"Rate limit exceeded for {client_ip}: {reason}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": reason,
                    "retry_after": 60
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Log successful request
        if response.status_code < 400:
            rate_limit_logger.debug(f"Request allowed for {client_ip} to {request.url.path}")
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP address"""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def _get_endpoint_type(self, request: Request) -> str:
        """Determine endpoint type for different rate limits"""
        path = request.url.path.lower()
        
        if "/auth" in path or "/login" in path or "/register" in path:
            return "auth"
        elif "/otp" in path or "/password" in path:
            return "otp"
        elif "/email-settings" in path:
            return "email_settings"
        elif "/api" in path:
            return "api"
        else:
            return "default"

# Utility functions for manual rate limiting
def check_ip_rate_limit(ip: str, limit: int = 50, window: int = 300) -> Tuple[bool, str]:
    """Check rate limit for specific IP"""
    return ip_rate_limiter.is_rate_limited(ip, limit, window)

def get_ip_statistics(ip: str) -> Dict:
    """Get rate limiting statistics for IP"""
    return ip_rate_limiter.get_ip_stats(ip)

def block_ip(ip: str, duration: int = 3600, reason: str = "Manual block"):
    """Manually block an IP address"""
    current_time = time.time()
    ip_rate_limiter.blocked_ips[ip] = (current_time + duration, 999)
    rate_limit_logger.warning(f"IP {ip} manually blocked for {duration} seconds: {reason}")

def unblock_ip(ip: str):
    """Manually unblock an IP address"""
    if ip in ip_rate_limiter.blocked_ips:
        del ip_rate_limiter.blocked_ips[ip]
        rate_limit_logger.info(f"IP {ip} manually unblocked")

def clear_all_rate_limits():
    """Clear all rate limiting data (useful for development)"""
    ip_rate_limiter.requests.clear()
    ip_rate_limiter.blocked_ips.clear()
    rate_limit_logger.info("All rate limiting data cleared")
