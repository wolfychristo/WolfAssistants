"""
Rate limiting for security-sensitive operations
"""
from fastapi import HTTPException, Request
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import time

class RateLimiter:
    """Rate limiting for security-sensitive operations"""
    
    def __init__(self):
        # In-memory store for rate limiting
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
    
    def _get_key(self, prefix: str, identifier: str) -> str:
        """Generate rate limit key"""
        return f"{prefix}:{identifier}"
    
    def _cleanup_expired(self, key: str):
        """Clean up expired entries"""
        if key in self.rate_limits:
            current_time = time.time()
            self.rate_limits[key]['attempts'] = [
                attempt_time for attempt_time in self.rate_limits[key]['attempts']
                if current_time - attempt_time < self.rate_limits[key]['window']
            ]
            
            # Remove empty entries
            if not self.rate_limits[key]['attempts']:
                del self.rate_limits[key]
    
    def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Check if rate limit is exceeded"""
        current_time = time.time()
        
        # Clean up expired entries
        self._cleanup_expired(key)
        
        if key not in self.rate_limits:
            self.rate_limits[key] = {
                'attempts': [],
                'window': window
            }
        
        # Remove old attempts outside the window
        self.rate_limits[key]['attempts'] = [
            attempt_time for attempt_time in self.rate_limits[key]['attempts']
            if current_time - attempt_time < window
        ]
        
        # Check if limit exceeded
        if len(self.rate_limits[key]['attempts']) >= limit:
            return False
        
        # Add current attempt
        self.rate_limits[key]['attempts'].append(current_time)
        return True
    
    def check_smtp_test_limit(self, user_id: int) -> bool:
        """Check SMTP test rate limit (5 tests per hour)"""
        key = self._get_key("smtp_test", str(user_id))
        return self.check_rate_limit(key, limit=5, window=3600)
    
    def check_password_reset_limit(self, email: str) -> bool:
        """Check password reset rate limit (3 attempts per hour)"""
        key = self._get_key("password_reset", email)
        return self.check_rate_limit(key, limit=3, window=3600)
    
    def check_credential_setup_limit(self, user_id: int) -> bool:
        """Check credential setup rate limit (10 attempts per hour)"""
        key = self._get_key("credential_setup", str(user_id))
        return self.check_rate_limit(key, limit=10, window=3600)
    
    def check_otp_generation_limit(self, email: str) -> bool:
        """Check OTP generation rate limit (5 attempts per hour)"""
        key = self._get_key("otp_generation", email)
        return self.check_rate_limit(key, limit=5, window=3600)
    
    def check_otp_verification_limit(self, email: str) -> bool:
        """Check OTP verification rate limit (10 attempts per hour)"""
        key = self._get_key("otp_verification", email)
        return self.check_rate_limit(key, limit=10, window=3600)

# Global rate limiter instance
rate_limiter = RateLimiter()

# FastAPI dependency for rate limiting
def check_smtp_test_rate_limit(request: Request, user_id: int):
    """Dependency to check SMTP test rate limit"""
    if not rate_limiter.check_smtp_test_limit(user_id):
        raise HTTPException(
            status_code=429,
            detail="SMTP test rate limit exceeded. Please try again later."
        )
    return True

def check_password_reset_rate_limit(request: Request, email: str):
    """Dependency to check password reset rate limit"""
    if not rate_limiter.check_password_reset_limit(email):
        raise HTTPException(
            status_code=429,
            detail="Password reset rate limit exceeded. Please try again later."
        )
    return True

def check_otp_generation_rate_limit(request: Request, email: str):
    """Dependency to check OTP generation rate limit"""
    if not rate_limiter.check_otp_generation_limit(email):
        raise HTTPException(
            status_code=429,
            detail="OTP generation rate limit exceeded. Please try again later."
        )
    return True

def check_otp_verification_rate_limit(request: Request, email: str):
    """Dependency to check OTP verification rate limit"""
    if not rate_limiter.check_otp_verification_limit(email):
        raise HTTPException(
            status_code=429,
            detail="OTP verification rate limit exceeded. Please try again later."
        )
    return True
