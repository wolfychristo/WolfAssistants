"""
Wolfy AI Key Manager

Manages multiple Wolfy AI API keys with load balancing, health monitoring,
and automatic failover for high availability.
"""

import asyncio
import time
import random
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from app.core.config import settings
from app.core.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)

class KeyStatus(Enum):
    """API key status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class KeyHealth:
    """API key health information."""
    key: str
    status: KeyStatus
    last_used: datetime
    last_success: datetime
    last_failure: datetime
    success_count: int = 0
    failure_count: int = 0
    response_time_avg: float = 0.0
    rate_limit_remaining: int = 60  # Default to minute limit
    rate_limit_reset: Optional[datetime] = None

class WolfyKeyManager:
    """Manages multiple Wolfy AI API keys with load balancing and health monitoring."""
    
    def __init__(self):
        self.keys: List[str] = []
        self.key_health: Dict[str, KeyHealth] = {}
        self.current_index = 0
        self._lock = asyncio.Lock()
        self._health_check_interval = 300  # 5 minutes
        self._last_health_check = datetime.min
        
        # Load keys from configuration
        self._load_keys()
        
        # Initialize health tracking
        self._initialize_health_tracking()
    
    def _load_keys(self):
        """Load API keys from configuration."""
        self.keys = settings.gemini_api_keys
        
        if not self.keys:
            logger.warning("No Gemini API keys found in configuration")
        else:
            logger.info(f"Loaded {len(self.keys)} Gemini API keys")
    
    def _initialize_health_tracking(self):
        """Initialize health tracking for all keys."""
        now = datetime.utcnow()
        for key in self.keys:
            # Mask key for logging (show only last 8 characters)
            masked_key = f"...{key[-8:]}" if len(key) > 8 else "***"
            
            self.key_health[key] = KeyHealth(
                key=key,
                status=KeyStatus.UNKNOWN,
                last_used=now,
                last_success=now,
                last_failure=now,
                success_count=0,
                failure_count=0,
                response_time_avg=0.0,
                rate_limit_remaining=60,
                rate_limit_reset=now + timedelta(minutes=1)
            )
            
            logger.info(f"Initialized health tracking for key: {masked_key}")
    
    async def get_next_key(self) -> Optional[str]:
        """Get the next available API key using round-robin with health checks."""
        async with self._lock:
            if not self.keys:
                logger.error("No API keys available")
                return None
            
            # Check if we need to perform health checks
            await self._perform_health_checks_if_needed()
            
            # Get healthy keys that aren't circuit-broken
            healthy_keys = [
                key for key, health in self.key_health.items()
                if (health.status in [KeyStatus.HEALTHY, KeyStatus.DEGRADED] and
                    not circuit_breaker.is_open(key))
            ]
            
            if not healthy_keys:
                logger.warning("No healthy API keys available, using any available key")
                healthy_keys = self.keys
            
            # Round-robin selection
            if healthy_keys:
                selected_key = healthy_keys[self.current_index % len(healthy_keys)]
                self.current_index = (self.current_index + 1) % len(healthy_keys)
                
                # Update last used time
                self.key_health[selected_key].last_used = datetime.utcnow()
                
                return selected_key
            
            return None
    
    async def get_random_key(self) -> Optional[str]:
        """Get a random healthy API key."""
        async with self._lock:
            if not self.keys:
                return None
            
            await self._perform_health_checks_if_needed()
            
            healthy_keys = [
                key for key, health in self.key_health.items()
                if (health.status in [KeyStatus.HEALTHY, KeyStatus.DEGRADED] and
                    not circuit_breaker.is_open(key))
            ]
            
            if not healthy_keys:
                healthy_keys = self.keys
            
            if healthy_keys:
                selected_key = random.choice(healthy_keys)
                self.key_health[selected_key].last_used = datetime.utcnow()
                return selected_key
            
            return None
    
    async def get_least_used_key(self) -> Optional[str]:
        """Get the least recently used healthy API key."""
        async with self._lock:
            if not self.keys:
                return None
            
            await self._perform_health_checks_if_needed()
            
            healthy_keys = [
                (key, health) for key, health in self.key_health.items()
                if (health.status in [KeyStatus.HEALTHY, KeyStatus.DEGRADED] and
                    not circuit_breaker.is_open(key))
            ]
            
            if not healthy_keys:
                healthy_keys = [(key, health) for key, health in self.key_health.items()]
            
            if healthy_keys:
                # Sort by last_used time (oldest first)
                healthy_keys.sort(key=lambda x: x[1].last_used)
                selected_key = healthy_keys[0][0]
                self.key_health[selected_key].last_used = datetime.utcnow()
                return selected_key
            
            return None
    
    async def record_success(self, key: str, response_time: float = 0.0):
        """Record a successful API call."""
        circuit_breaker.record_success(key)
        
        if key not in self.key_health:
            return
        
        health = self.key_health[key]
        health.success_count += 1
        health.last_success = datetime.utcnow()
        
        # Update average response time
        if health.response_time_avg == 0:
            health.response_time_avg = response_time
        else:
            health.response_time_avg = (health.response_time_avg + response_time) / 2
        
        # Update status based on success rate
        total_calls = health.success_count + health.failure_count
        success_rate = health.success_count / total_calls if total_calls > 0 else 1.0
        
        if success_rate >= 0.95:
            health.status = KeyStatus.HEALTHY
        elif success_rate >= 0.8:
            health.status = KeyStatus.DEGRADED
        else:
            health.status = KeyStatus.UNHEALTHY
    
    async def record_failure(self, key: str, error_type: str = "unknown"):
        """Record a failed API call."""
        circuit_breaker.record_failure(key)
        
        if key not in self.key_health:
            return
        
        health = self.key_health[key]
        health.failure_count += 1
        health.last_failure = datetime.utcnow()
        
        # Update status based on failure rate
        total_calls = health.success_count + health.failure_count
        failure_rate = health.failure_count / total_calls if total_calls > 0 else 0.0
        
        if failure_rate >= 0.5:
            health.status = KeyStatus.UNHEALTHY
        elif failure_rate >= 0.2:
            health.status = KeyStatus.DEGRADED
        else:
            health.status = KeyStatus.HEALTHY
        
        logger.warning(f"API key failure recorded: {error_type} for key ...{key[-8:]}")
    
    async def update_rate_limit(self, key: str, remaining: int, reset_time: datetime):
        """Update rate limit information for a key."""
        if key not in self.key_health:
            return
        
        health = self.key_health[key]
        health.rate_limit_remaining = remaining
        health.rate_limit_reset = reset_time
    
    async def _perform_health_checks_if_needed(self):
        """Perform health checks if enough time has passed."""
        now = datetime.utcnow()
        if (now - self._last_health_check).total_seconds() < self._health_check_interval:
            return
        
        self._last_health_check = now
        await self._perform_health_checks()
    
    async def _perform_health_checks(self):
        """Perform health checks on all keys."""
        logger.info("Performing health checks on all API keys...")
        
        for key in self.keys:
            health = self.key_health[key]
            
            # Check if key has been used recently
            time_since_use = (datetime.utcnow() - health.last_used).total_seconds()
            
            # If key hasn't been used in 1 hour, mark as unknown
            if time_since_use > 3600:
                health.status = KeyStatus.UNKNOWN
            
            # Check rate limit reset
            if health.rate_limit_reset and datetime.utcnow() >= health.rate_limit_reset:
                health.rate_limit_remaining = 60  # Reset to default
    
    def get_health_status(self) -> Dict[str, Dict]:
        """Get health status of all keys."""
        status = {}
        
        for key, health in self.key_health.items():
            masked_key = f"...{key[-8:]}" if len(key) > 8 else "***"
            
            status[masked_key] = {
                "status": health.status.value,
                "last_used": health.last_used.isoformat(),
                "last_success": health.last_success.isoformat(),
                "last_failure": health.last_failure.isoformat() if health.last_failure else None,
                "success_count": health.success_count,
                "failure_count": health.failure_count,
                "success_rate": health.success_count / (health.success_count + health.failure_count) if (health.success_count + health.failure_count) > 0 else 0,
                "response_time_avg": health.response_time_avg,
                "rate_limit_remaining": health.rate_limit_remaining,
                "rate_limit_reset": health.rate_limit_reset.isoformat() if health.rate_limit_reset else None
            }
        
        return status
    
    def get_available_keys_count(self) -> int:
        """Get count of available (healthy) keys."""
        return len([
            key for key, health in self.key_health.items()
            if health.status in [KeyStatus.HEALTHY, KeyStatus.DEGRADED]
        ])
    
    def get_total_keys_count(self) -> int:
        """Get total number of configured keys."""
        return len(self.keys)

# Global key manager instance
key_manager = WolfyKeyManager()
