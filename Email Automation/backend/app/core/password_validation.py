"""
Password validation utilities including HaveIBeenPwned leak detection.
Uses the free k-anonymity API to check passwords against known breaches.
Optimized with caching and reduced timeout for better performance.
"""
import hashlib
import httpx
from typing import Optional, Tuple
from fastapi import HTTPException
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# In-memory cache for breach check results
# Format: {password_hash: (is_breached: bool, cached_at: datetime)}
_breach_cache: dict[str, tuple[bool, datetime]] = {}
_cache_ttl = timedelta(hours=24)  # Cache results for 24 hours
_max_cache_size = 10000  # Limit cache size to prevent memory issues


def _cleanup_cache():
    """Remove expired entries from cache to prevent memory bloat."""
    global _breach_cache
    now = datetime.utcnow()
    expired_keys = [
        key for key, (_, cached_at) in _breach_cache.items()
        if now - cached_at > _cache_ttl
    ]
    for key in expired_keys:
        _breach_cache.pop(key, None)
    
    # If cache is still too large, remove oldest entries
    if len(_breach_cache) > _max_cache_size:
        sorted_items = sorted(
            _breach_cache.items(),
            key=lambda x: x[1][1]  # Sort by cached_at timestamp
        )
        # Remove oldest 20% of entries
        remove_count = len(sorted_items) - int(_max_cache_size * 0.8)
        for key, _ in sorted_items[:remove_count]:
            _breach_cache.pop(key, None)


async def check_password_breached(password: str) -> bool:
    """
    Check if a password has been found in data breaches using HaveIBeenPwned API.
    
    Uses k-anonymity: only sends first 5 chars of SHA-1 hash, receives all matching
    hashes, then checks locally. This protects user privacy.
    
    Optimized with:
    - In-memory caching (24-hour TTL)
    - Reduced timeout (2 seconds instead of 5)
    - Automatic cache cleanup
    
    Args:
        password: The password to check
        
    Returns:
        True if password is found in breaches, False otherwise
    """
    # Create SHA-1 hash of password for cache key
    password_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    
    # Check cache first
    if password_hash in _breach_cache:
        is_breached, cached_at = _breach_cache[password_hash]
        # Check if cache entry is still valid
        if datetime.utcnow() - cached_at < _cache_ttl:
            logger.debug(f"Password breach check cache hit for hash prefix {password_hash[:5]}")
            return is_breached
        else:
            # Remove expired entry
            _breach_cache.pop(password_hash, None)
    
    # Cleanup cache periodically (every 100 checks)
    if len(_breach_cache) % 100 == 0:
        _cleanup_cache()
    
    try:
        # Get first 5 characters (k-anonymity)
        hash_prefix = password_hash[:5]
        hash_suffix = password_hash[5:]
        
        # Query HaveIBeenPwned range API (free, no API key needed)
        url = f"https://api.pwnedpasswords.com/range/{hash_prefix}"
        
        # Reduced timeout from 5.0 to 2.0 seconds for faster failure
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Response contains all hashes starting with prefix (one per line)
            # Format: SUFFIX:COUNT (e.g., "0018A45C4D1DEF81644B54AB7F969B88D65:123456")
            breached_hashes = response.text
            
            # Check if our hash suffix appears in the response
            is_breached = False
            for line in breached_hashes.splitlines():
                if ':' in line:
                    suffix, count = line.split(':', 1)
                    if suffix == hash_suffix:
                        logger.warning(f"Password breach check found compromised password (count: {count})")
                        is_breached = True
                        break
            
            # Cache the result
            _breach_cache[password_hash] = (is_breached, datetime.utcnow())
            return is_breached
                        
    except httpx.TimeoutException:
        # API timeout - allow password but log warning
        logger.warning("HaveIBeenPwned API timeout (2s) - allowing password but breach check failed")
        # Cache as safe to avoid repeated timeouts for same password
        _breach_cache[password_hash] = (False, datetime.utcnow())
        return False
    except httpx.HTTPError as e:
        # API error - allow password but log warning
        logger.warning(f"HaveIBeenPwned API error - allowing password but breach check failed: {e}")
        # Don't cache errors - retry next time
        return False
    except Exception as e:
        # Unexpected error - allow password but log warning
        logger.error(f"Unexpected error in password breach check - allowing password: {e}")
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength requirements.
    
    Args:
        password: The password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    
    if len(password) > 128:
        return False, "Password must be no more than 128 characters long."
    
    # Check for at least one letter and one number (optional enhancement)
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)
    
    if not has_letter:
        return False, "Password must contain at least one letter."
    
    if not has_number:
        return False, "Password must contain at least one number."
    
    return True, ""


async def validate_password(password: str, check_breach: bool = True) -> None:
    """
    Comprehensive password validation including breach checking.
    
    Args:
        password: The password to validate
        check_breach: Whether to check HaveIBeenPwned (default: True)
        
    Raises:
        HTTPException: If password fails validation
    """
    # Check password strength
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )
    
    # Check for breached passwords
    if check_breach:
        is_breached = await check_password_breached(password)
        if is_breached:
            raise HTTPException(
                status_code=400,
                detail="This password has been found in data breaches and is not secure. Please choose a different password."
            )

