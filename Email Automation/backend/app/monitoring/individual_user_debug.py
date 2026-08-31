#!/usr/bin/env python3
"""
Minimal replacement for individual_user_debug module
This provides the same interface but with minimal functionality
"""

from enum import Enum
from typing import Dict, Any, Optional
import logging

# Configure logger
logger = logging.getLogger(__name__)

class DebugLevel(Enum):
    """Debug level enumeration"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error category enumeration"""
    UNKNOWN = "unknown"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    RATE_LIMIT = "rate_limit"
    DATABASE = "database"
    NETWORK = "network"
    SYSTEM = "system"

class IndividualUserDebugger:
    """Minimal individual user debugger - provides interface but minimal functionality"""
    
    def __init__(self):
        self.logger = logger
    
    async def log_user_activity(
        self,
        user_id: int,
        email: str,
        action: str,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log user activity - minimal implementation"""
        try:
            self.logger.info(f"User activity: {user_id} ({email}) - {action}")
        except Exception as e:
            self.logger.error(f"Failed to log user activity: {e}")
    
    async def log_user_error(
        self,
        user_id: int,
        email: str,
        error_category: ErrorCategory,
        error_message: str,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: DebugLevel = DebugLevel.ERROR
    ):
        """Log user error - minimal implementation"""
        try:
            self.logger.error(f"User error: {user_id} ({email}) - {error_category.value}: {error_message}")
        except Exception as e:
            self.logger.error(f"Failed to log user error: {e}")

# Global instance
individual_user_debugger = IndividualUserDebugger()

async def cleanup_debug_data():
    """Cleanup debug data - minimal implementation"""
    try:
        logger.info("Debug data cleanup completed (minimal implementation)")
    except Exception as e:
        logger.error(f"Failed to cleanup debug data: {e}")
