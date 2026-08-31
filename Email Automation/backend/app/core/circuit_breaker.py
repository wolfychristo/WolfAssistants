"""
Circuit Breaker Pattern
Prevents cascading failures by temporarily disabling unhealthy API keys
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 timeout: int = 60,
                 success_threshold: int = 2):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # seconds
        self.success_threshold = success_threshold
        
        self.failure_count: Dict[str, int] = {}
        self.opened_at: Dict[str, datetime] = {}
        self.state: Dict[str, CircuitState] = {}
        self.half_open_successes: Dict[str, int] = {}
    
    def is_open(self, key: str) -> bool:
        """Check if circuit is open for this key"""
        if key not in self.state:
            self.state[key] = CircuitState.CLOSED
            return False
        
        if self.state[key] == CircuitState.OPEN:
            # Check if timeout has passed
            if key in self.opened_at:
                elapsed = (datetime.utcnow() - self.opened_at[key]).total_seconds()
                if elapsed > self.timeout:
                    # Transition to half-open
                    self.state[key] = CircuitState.HALF_OPEN
                    self.half_open_successes[key] = 0
                    logger.info(f"Circuit breaker for {key[:8]}... transitioning to HALF_OPEN")
                    return False
            return True
        
        return False
    
    def record_success(self, key: str):
        """Record successful call"""
        if key in self.failure_count:
            del self.failure_count[key]
        
        if self.state.get(key) == CircuitState.HALF_OPEN:
            self.half_open_successes[key] = self.half_open_successes.get(key, 0) + 1
            
            if self.half_open_successes[key] >= self.success_threshold:
                # Circuit recovered
                self.state[key] = CircuitState.CLOSED
                if key in self.opened_at:
                    del self.opened_at[key]
                if key in self.half_open_successes:
                    del self.half_open_successes[key]
                logger.info(f"Circuit breaker for {key[:8]}... CLOSED (recovered)")
        else:
            self.state[key] = CircuitState.CLOSED
    
    def record_failure(self, key: str):
        """Record failure, open circuit if threshold reached"""
        self.failure_count[key] = self.failure_count.get(key, 0) + 1
        
        if self.state.get(key) == CircuitState.HALF_OPEN:
            # Failure during half-open, immediately open again
            self.state[key] = CircuitState.OPEN
            self.opened_at[key] = datetime.utcnow()
            logger.warning(f"Circuit breaker for {key[:8]}... OPEN (failed during half-open)")
        elif self.failure_count[key] >= self.failure_threshold:
            self.state[key] = CircuitState.OPEN
            self.opened_at[key] = datetime.utcnow()
            logger.warning(f"Circuit breaker for {key[:8]}... OPEN ({self.failure_count[key]} failures)")
    
    def get_state(self, key: str) -> CircuitState:
        """Get current circuit state for a key"""
        return self.state.get(key, CircuitState.CLOSED)
    
    def get_stats(self) -> Dict[str, Dict]:
        """Get circuit breaker statistics"""
        stats = {}
        for key, state in self.state.items():
            masked_key = f"...{key[-8:]}" if len(key) > 8 else "***"
            stats[masked_key] = {
                'state': state.value,
                'failure_count': self.failure_count.get(key, 0),
                'opened_at': self.opened_at[key].isoformat() if key in self.opened_at else None
            }
        return stats


# Global circuit breaker instance
circuit_breaker = CircuitBreaker()

