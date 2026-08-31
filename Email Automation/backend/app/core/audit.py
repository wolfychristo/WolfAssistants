"""
Comprehensive audit logging for security events
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User

# Configure audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Create file handler for audit logs
if not audit_logger.handlers:
    handler = logging.FileHandler("audit.log")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    audit_logger.addHandler(handler)

class AuditLogger:
    """Centralized audit logging for security events"""
    
    @staticmethod
    def log_smtp_credential_access(user_id: int, action: str, success: bool, details: str = ""):
        """Log SMTP credential access"""
        audit_logger.info(f"SMTP_ACCESS|user_id:{user_id}|action:{action}|success:{success}|details:{details}")
    
    @staticmethod
    def log_password_reset_attempt(email: str, success: bool, ip_address: str = ""):
        """Log password reset attempts"""
        audit_logger.info(f"PASSWORD_RESET|email:{email}|success:{success}|ip:{ip_address}")
    
    @staticmethod
    def log_smtp_test_attempt(user_id: int, success: bool, error: str = ""):
        """Log SMTP test attempts"""
        audit_logger.info(f"SMTP_TEST|user_id:{user_id}|success:{success}|error:{error}")
    
    @staticmethod
    def log_credential_health_check(user_id: int, status: str, details: str = ""):
        """Log credential health checks"""
        audit_logger.info(f"CREDENTIAL_HEALTH|user_id:{user_id}|status:{status}|details:{details}")
    
    @staticmethod
    def log_suspicious_activity(user_id: int, activity: str, details: str = ""):
        """Log suspicious activities"""
        audit_logger.warning(f"SUSPICIOUS_ACTIVITY|user_id:{user_id}|activity:{activity}|details:{details}")
    
    @staticmethod
    def log_otp_generation(email: str, success: bool):
        """Log OTP generation"""
        audit_logger.info(f"OTP_GENERATION|email:{email}|success:{success}")
    
    @staticmethod
    def log_otp_verification(email: str, success: bool, attempts: int = 1):
        """Log OTP verification"""
        audit_logger.info(f"OTP_VERIFICATION|email:{email}|success:{success}|attempts:{attempts}")
    
    @staticmethod
    def log_password_change(user_id: int, success: bool):
        """Log password changes"""
        audit_logger.info(f"PASSWORD_CHANGE|user_id:{user_id}|success:{success}")

# Global audit logger instance
audit = AuditLogger()
