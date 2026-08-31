"""
Security audit system for WolfAssistants
Comprehensive monitoring and threat detection
"""
import time
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from collections import defaultdict, deque
import os

# Configure security audit logger
audit_logger = logging.getLogger("security_audit")
audit_logger.setLevel(logging.INFO)

# Create file handler for audit logs
if not os.path.exists("logs"):
    os.makedirs("logs")

file_handler = logging.FileHandler("logs/security_audit.log")
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
audit_logger.addHandler(file_handler)

class ThreatLevel(Enum):
    """Threat level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EventType(Enum):
    """Security event types"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    PASSWORD_RESET = "password_reset"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_ACCESS = "data_access"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_ERROR = "system_error"
    IP_BLOCKED = "ip_blocked"
    IP_UNBLOCKED = "ip_unblocked"
    ADMIN_ACTION = "admin_action"

@dataclass
class SecurityEvent:
    """Security event record"""
    timestamp: str
    event_type: str
    threat_level: str
    ip_address: str
    user_agent: str
    user_id: Optional[str]
    endpoint: str
    method: str
    description: str
    details: Dict[str, Any]
    request_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class SecurityAuditor:
    """Comprehensive security audit system"""
    
    def __init__(self):
        self.events: deque = deque(maxlen=10000)  # Keep last 10k events
        self.ip_stats: Dict[str, Dict] = defaultdict(lambda: {
            'request_count': 0,
            'error_count': 0,
            'last_seen': None,
            'threat_score': 0,
            'blocked': False,
            'violations': []
        })
        self.user_stats: Dict[str, Dict] = defaultdict(lambda: {
            'login_attempts': 0,
            'failed_logins': 0,
            'last_login': None,
            'suspicious_activity': 0
        })
        self.threat_patterns = [
            'sql injection', 'xss', 'csrf', 'directory traversal',
            'command injection', 'ldap injection', 'nosql injection',
            'brute force', 'dictionary attack', 'credential stuffing'
        ]
        self.cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        # Don't start the task during module import
        # It will be started when the application starts
        self.cleanup_task = None
    
    async def _cleanup_loop(self):
        """Background cleanup of old data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour
                await self._cleanup_old_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                audit_logger.error(f"Security audit cleanup error: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data to prevent memory leaks"""
        current_time = time.time()
        cutoff_time = current_time - (7 * 24 * 3600)  # 7 days ago
        
        # Clean up old IP stats
        for ip in list(self.ip_stats.keys()):
            ip_data = self.ip_stats[ip]
            if ip_data['last_seen'] and ip_data['last_seen'] < cutoff_time:
                del self.ip_stats[ip]
        
        # Clean up old user stats
        for user_id in list(self.user_stats.keys()):
            user_data = self.user_stats[user_id]
            if user_data['last_login'] and user_data['last_login'] < cutoff_time:
                del self.user_stats[user_id]
    
    def log_event(self, event_type: EventType, threat_level: ThreatLevel, 
                  ip_address: str, user_agent: str, user_id: Optional[str],
                  endpoint: str, method: str, description: str, 
                  details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
        """Log a security event"""
        if details is None:
            details = {}
        
        if request_id is None:
            request_id = self._generate_request_id(ip_address, endpoint, method)
        
        event = SecurityEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type.value,
            threat_level=threat_level.value,
            ip_address=ip_address,
            user_agent=user_agent or "Unknown",
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            description=description,
            details=details,
            request_id=request_id
        )
        
        # Store event
        self.events.append(event)
        
        # Update statistics
        self._update_ip_stats(ip_address, event_type, threat_level)
        if user_id:
            self._update_user_stats(user_id, event_type, threat_level)
        
        # Log to file
        audit_logger.info(f"SECURITY_EVENT: {json.dumps(event.to_dict())}")
        
        # Check for threats
        self._check_threats(ip_address, user_id)
    
    def _generate_request_id(self, ip_address: str, endpoint: str, method: str) -> str:
        """Generate unique request ID"""
        data = f"{ip_address}{endpoint}{method}{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _update_ip_stats(self, ip_address: str, event_type: EventType, threat_level: ThreatLevel):
        """Update IP statistics"""
        stats = self.ip_stats[ip_address]
        stats['request_count'] += 1
        stats['last_seen'] = time.time()
        
        if event_type in [EventType.LOGIN_FAILURE, EventType.RATE_LIMIT_EXCEEDED, 
                         EventType.SUSPICIOUS_ACTIVITY, EventType.SQL_INJECTION_ATTEMPT,
                         EventType.XSS_ATTEMPT, EventType.UNAUTHORIZED_ACCESS]:
            stats['error_count'] += 1
            stats['threat_score'] += self._get_threat_score(threat_level)
            stats['violations'].append({
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type.value,
                'threat_level': threat_level.value
            })
    
    def _update_user_stats(self, user_id: str, event_type: EventType, threat_level: ThreatLevel):
        """Update user statistics"""
        stats = self.user_stats[user_id]
        
        if event_type == EventType.LOGIN_SUCCESS:
            stats['login_attempts'] += 1
            stats['last_login'] = time.time()
        elif event_type == EventType.LOGIN_FAILURE:
            stats['failed_logins'] += 1
        elif event_type == EventType.SUSPICIOUS_ACTIVITY:
            stats['suspicious_activity'] += 1
    
    def _get_threat_score(self, threat_level: ThreatLevel) -> int:
        """Get threat score based on threat level"""
        scores = {
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 3,
            ThreatLevel.HIGH: 5,
            ThreatLevel.CRITICAL: 10
        }
        return scores.get(threat_level, 1)
    
    def _check_threats(self, ip_address: str, user_id: Optional[str]):
        """Check for potential threats"""
        ip_stats = self.ip_stats[ip_address]
        
        # Check for high threat score
        if ip_stats['threat_score'] > 20:
            self.log_event(
                EventType.IP_BLOCKED,
                ThreatLevel.HIGH,
                ip_address,
                "System",
                None,
                "security_audit",
                "AUTO",
                f"IP {ip_address} blocked due to high threat score: {ip_stats['threat_score']}",
                {'threat_score': ip_stats['threat_score'], 'violations': len(ip_stats['violations'])}
            )
            ip_stats['blocked'] = True
        
        # Check for rapid failed logins
        if user_id and self.user_stats[user_id]['failed_logins'] > 5:
            self.log_event(
                EventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.MEDIUM,
                ip_address,
                "System",
                user_id,
                "security_audit",
                "AUTO",
                f"User {user_id} has {self.user_stats[user_id]['failed_logins']} failed login attempts",
                {'failed_logins': self.user_stats[user_id]['failed_logins']}
            )
    
    def get_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate security report for specified hours"""
        cutoff_time = time.time() - (hours * 3600)
        
        # Filter events within time range
        recent_events = [
            event for event in self.events
            if datetime.fromisoformat(event.timestamp).timestamp() > cutoff_time
        ]
        
        # Count events by type
        event_counts = defaultdict(int)
        threat_counts = defaultdict(int)
        ip_counts = defaultdict(int)
        
        for event in recent_events:
            event_counts[event.event_type] += 1
            threat_counts[event.threat_level] += 1
            ip_counts[event.ip_address] += 1
        
        # Get top suspicious IPs
        suspicious_ips = sorted(
            [(ip, stats['threat_score']) for ip, stats in self.ip_stats.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Get top suspicious users
        suspicious_users = sorted(
            [(user_id, stats['suspicious_activity']) for user_id, stats in self.user_stats.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'report_period_hours': hours,
            'total_events': len(recent_events),
            'event_counts': dict(event_counts),
            'threat_counts': dict(threat_counts),
            'unique_ips': len(ip_counts),
            'suspicious_ips': suspicious_ips,
            'suspicious_users': suspicious_users,
            'blocked_ips': [ip for ip, stats in self.ip_stats.items() if stats['blocked']],
            'generated_at': datetime.now().isoformat()
        }
    
    def get_ip_analysis(self, ip_address: str) -> Dict[str, Any]:
        """Get detailed analysis for specific IP"""
        if ip_address not in self.ip_stats:
            return {'error': 'IP not found'}
        
        stats = self.ip_stats[ip_address]
        
        # Get recent events for this IP
        recent_events = [
            event for event in self.events
            if event.ip_address == ip_address
        ][-50:]  # Last 50 events
        
        return {
            'ip_address': ip_address,
            'request_count': stats['request_count'],
            'error_count': stats['error_count'],
            'threat_score': stats['threat_score'],
            'blocked': stats['blocked'],
            'last_seen': stats['last_seen'],
            'violations': stats['violations'],
            'recent_events': [event.to_dict() for event in recent_events]
        }
    
    def get_user_analysis(self, user_id: str) -> Dict[str, Any]:
        """Get detailed analysis for specific user"""
        if user_id not in self.user_stats:
            return {'error': 'User not found'}
        
        stats = self.user_stats[user_id]
        
        # Get recent events for this user
        recent_events = [
            event for event in self.events
            if event.user_id == user_id
        ][-50:]  # Last 50 events
        
        return {
            'user_id': user_id,
            'login_attempts': stats['login_attempts'],
            'failed_logins': stats['failed_logins'],
            'suspicious_activity': stats['suspicious_activity'],
            'last_login': stats['last_login'],
            'recent_events': [event.to_dict() for event in recent_events]
        }

# Global security auditor instance
security_auditor = SecurityAuditor()

# Utility functions
def log_security_event(event_type: EventType, threat_level: ThreatLevel, 
                      ip_address: str, user_agent: str, user_id: Optional[str],
                      endpoint: str, method: str, description: str, 
                      details: Optional[Dict[str, Any]] = None):
    """Log a security event"""
    security_auditor.log_event(
        event_type, threat_level, ip_address, user_agent, user_id,
        endpoint, method, description, details
    )

def get_security_report(hours: int = 24) -> Dict[str, Any]:
    """Get security report"""
    return security_auditor.get_security_report(hours)

def get_ip_analysis(ip_address: str) -> Dict[str, Any]:
    """Get IP analysis"""
    return security_auditor.get_ip_analysis(ip_address)

def get_user_analysis(user_id: str) -> Dict[str, Any]:
    """Get user analysis"""
    return security_auditor.get_user_analysis(user_id)
