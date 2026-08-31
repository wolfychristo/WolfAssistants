"""
Comprehensive health checking system for WolfAssistants
Monitors all features and provides detailed status reports
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import requests
from sqlalchemy import text
from app.core.database import SessionLocal
from app.core.config import settings

# Configure health check logger
health_logger = logging.getLogger("health_checker")

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    MAINTENANCE = "maintenance"

@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    response_time: float
    error_message: Optional[str] = None
    last_check: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None

class HealthChecker:
    """Comprehensive health checking system"""
    
    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.check_interval = 30  # seconds
        self._monitoring_task = None
        self._start_monitoring()
    
    def _start_monitoring(self):
        """Start background health monitoring"""
        # Don't start the task during module import
        # It will be started when the application starts
        self._monitoring_task = None
    
    async def _monitoring_loop(self):
        """Background health monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._run_all_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                health_logger.error(f"Health monitoring error: {e}")
    
    async def _run_all_checks(self):
        """Run all health checks"""
        checks = [
            self._check_database,
            self._check_email_service,
            self._check_gemini_api,
            self._check_wolfy_chat,
            self._check_otp_service,
            self._check_file_system,
            self._check_memory_usage,
            self._check_disk_space
        ]
        
        for check_func in checks:
            try:
                await check_func()
            except Exception as e:
                health_logger.error(f"Health check {check_func.__name__} failed: {e}")
    
    async def _check_database(self):
        """Check database connectivity and performance"""
        start_time = time.time()
        try:
            db = SessionLocal()
            try:
                # Test basic query
                result = db.execute(text("SELECT 1")).fetchone()
                if not result:
                    raise Exception("Database query returned no results")
                
                # Test table access
                db.execute(text("SELECT COUNT(*) FROM users")).fetchone()
                
                response_time = time.time() - start_time
                self.checks["database"] = HealthCheck(
                    name="Database",
                    status=HealthStatus.HEALTHY,
                    response_time=response_time,
                    last_check=datetime.now(),
                    details={"query_time": response_time}
                )
                
            finally:
                db.close()
                
        except Exception as e:
            self.checks["database"] = HealthCheck(
                name="Database",
                status=HealthStatus.DOWN,
                response_time=time.time() - start_time,
                error_message=str(e),
                last_check=datetime.now()
            )
    
    async def _check_email_service(self):
        """Check email service configuration and connectivity"""
        start_time = time.time()
        try:
            # Check if SMTP settings are configured
            if not settings.SYSTEM_EMAIL_HOST:
                raise Exception("SMTP host not configured")
            
            # Test SMTP connection (simplified check)
            import smtplib
            import ssl
            
            context = ssl.create_default_context()
            port = settings.SYSTEM_EMAIL_PORT or 587
            user = settings.SYSTEM_EMAIL_USER or ""
            password = settings.SYSTEM_EMAIL_PASSWORD or ""
            
            with smtplib.SMTP(settings.SYSTEM_EMAIL_HOST, port) as server:
                server.starttls(context=context)
                server.login(user, password)
            
            response_time = time.time() - start_time
            self.checks["email_service"] = HealthCheck(
                name="Email Service",
                status=HealthStatus.HEALTHY,
                response_time=response_time,
                last_check=datetime.now(),
                details={"smtp_host": settings.SYSTEM_EMAIL_HOST}
            )
            
        except Exception as e:
            self.checks["email_service"] = HealthCheck(
                name="Email Service",
                status=HealthStatus.DOWN,
                response_time=time.time() - start_time,
                error_message=str(e),
                last_check=datetime.now()
            )
    
    async def _check_gemini_api(self):
        """Check Gemini API connectivity"""
        start_time = time.time()
        try:
            if not settings.GEMINI_API_KEY:
                raise Exception("Gemini API key not configured")
            
            # Test API with a simple request
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("Test")
            
            response_time = time.time() - start_time
            self.checks["gemini_api"] = HealthCheck(
                name="Gemini API",
                status=HealthStatus.HEALTHY,
                response_time=response_time,
                last_check=datetime.now()
            )
            
        except Exception as e:
            self.checks["gemini_api"] = HealthCheck(
                name="Gemini API",
                status=HealthStatus.DOWN,
                response_time=time.time() - start_time,
                error_message=str(e),
                last_check=datetime.now()
            )
    
    async def _check_wolfy_chat(self):
        """Check Wolfy chat functionality"""
        start_time = time.time()
        try:
            # Test internal Wolfy functionality
            from app.api.v1.simon import _detect_query_complexity
            
            # Test with a simple query
            complexity = _detect_query_complexity("Hello")
            
            response_time = time.time() - start_time
            self.checks["wolfy_chat"] = HealthCheck(
                name="Wolfy Chat",
                status=HealthStatus.HEALTHY,
                response_time=response_time,
                last_check=datetime.now(),
                details={"complexity_detection": complexity}
            )
            
        except Exception as e:
            self.checks["wolfy_chat"] = HealthCheck(
                name="Wolfy Chat",
                status=HealthStatus.DOWN,
                response_time=time.time() - start_time,
                error_message=str(e),
                last_check=datetime.now()
            )
    
    async def _check_otp_service(self):
        """Check OTP generation and validation"""
        start_time = time.time()
        try:
            from app.core.otp_utils import generate_structured_otp, validate_structured_otp
            
            # Test OTP generation
            otp = generate_structured_otp()
            if not otp or len(otp) != 6:
                raise Exception("OTP generation failed")
            
            # Test OTP validation
            if not validate_structured_otp(otp):
                raise Exception("OTP validation failed")
            
            response_time = time.time() - start_time
            self.checks["otp_service"] = HealthCheck(
                name="OTP Service",
                status=HealthStatus.HEALTHY,
                response_time=response_time,
                last_check=datetime.now(),
                details={"otp_length": len(otp)}
            )
            
        except Exception as e:
            self.checks["otp_service"] = HealthCheck(
                name="OTP Service",
                status=HealthStatus.DOWN,
                response_time=time.time() - start_time,
                error_message=str(e),
                last_check=datetime.now()
            )
    
    async def _check_file_system(self):
        """Check file system access and disk space"""
        start_time = time.time()
        try:
            import os
            import shutil
            
            # Check if we can write to the current directory
            test_file = "health_check_test.tmp"
            with open(test_file, "w") as f:
                f.write("test")
            
            # Check disk space
            disk_usage = shutil.disk_usage(".")
            free_space_gb = disk_usage.free / (1024**3)
            
            # Clean up test file
            os.remove(test_file)
            
            status = HealthStatus.HEALTHY
            if free_space_gb < 1:  # Less than 1GB free
                status = HealthStatus.DEGRADED
            
            response_time = time.time() - start_time
            self.checks["file_system"] = HealthCheck(
                name="File System",
                status=status,
                response_time=response_time,
                last_check=datetime.now(),
                details={"free_space_gb": round(free_space_gb, 2)}
            )
            
        except Exception as e:
            self.checks["file_system"] = HealthCheck(
                name="File System",
                status=HealthStatus.DOWN,
                response_time=time.time() - start_time,
                error_message=str(e),
                last_check=datetime.now()
            )
    
    async def _check_memory_usage(self):
        """Check memory usage"""
        start_time = time.time()
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            status = HealthStatus.HEALTHY
            if memory_percent > 90:
                status = HealthStatus.DOWN
            elif memory_percent > 80:
                status = HealthStatus.DEGRADED
            
            response_time = time.time() - start_time
            self.checks["memory"] = HealthCheck(
                name="Memory",
                status=status,
                response_time=response_time,
                last_check=datetime.now(),
                details={"usage_percent": memory_percent, "available_gb": round(memory.available / (1024**3), 2)}
            )
            
        except Exception as e:
            self.checks["memory"] = HealthCheck(
                name="Memory",
                status=HealthStatus.DOWN,
                response_time=time.time() - start_time,
                error_message=str(e),
                last_check=datetime.now()
            )
    
    async def _check_disk_space(self):
        """Check disk space usage"""
        start_time = time.time()
        try:
            import psutil
            
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            status = HealthStatus.HEALTHY
            if disk_percent > 95:
                status = HealthStatus.DOWN
            elif disk_percent > 85:
                status = HealthStatus.DEGRADED
            
            response_time = time.time() - start_time
            self.checks["disk_space"] = HealthCheck(
                name="Disk Space",
                status=status,
                response_time=response_time,
                last_check=datetime.now(),
                details={"usage_percent": round(disk_percent, 2), "free_gb": round(disk.free / (1024**3), 2)}
            )
            
        except Exception as e:
            self.checks["disk_space"] = HealthCheck(
                name="Disk Space",
                status=HealthStatus.DOWN,
                response_time=time.time() - start_time,
                error_message=str(e),
                last_check=datetime.now()
            )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        if not self.checks:
            return {"status": "unknown", "message": "No health checks performed yet"}
        
        # Determine overall status
        statuses = [check.status for check in self.checks.values()]
        if HealthStatus.DOWN in statuses:
            overall_status = "down"
        elif HealthStatus.DEGRADED in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": {
                name: {
                    "status": check.status,
                    "response_time": check.response_time,
                    "error_message": check.error_message,
                    "last_check": check.last_check.isoformat() if check.last_check else None,
                    "details": check.details or {}
                }
                for name, check in self.checks.items()
            }
        }
    
    def get_feature_health(self, feature: str) -> Optional[HealthCheck]:
        """Get health status for a specific feature"""
        return self.checks.get(feature)

# Global instance
health_checker = HealthChecker()
