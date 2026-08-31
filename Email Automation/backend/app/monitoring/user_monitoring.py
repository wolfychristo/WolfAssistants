"""
User monitoring and management system for WolfAssistants
Handles 100+ concurrent users with proper resource management
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import psutil
import time

# Configure monitoring logger
monitoring_logger = logging.getLogger("user_monitoring")

class UserStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    BLOCKED = "blocked"
    SUSPENDED = "suspended"

class FeatureStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    MAINTENANCE = "maintenance"

@dataclass
class UserSession:
    user_id: int
    email: str
    last_activity: datetime
    request_count: int
    status: UserStatus
    features_used: Set[str]
    ip_address: str
    session_start: datetime

@dataclass
class FeatureHealth:
    name: str
    status: FeatureStatus
    response_time: float
    error_rate: float
    last_check: datetime
    user_count: int
    max_capacity: int

class UserMonitor:
    """Comprehensive user monitoring and management system"""
    
    def __init__(self):
        # User sessions tracking
        self.active_sessions: Dict[int, UserSession] = {}
        self.user_activity: Dict[int, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Feature health tracking
        self.feature_health: Dict[str, FeatureHealth] = {
            "email_generation": FeatureHealth("email_generation", FeatureStatus.HEALTHY, 0.0, 0.0, datetime.now(), 0, 50),
            "wolfy_chat": FeatureHealth("wolfy_chat", FeatureStatus.HEALTHY, 0.0, 0.0, datetime.now(), 0, 30),
            "contact_management": FeatureHealth("contact_management", FeatureStatus.HEALTHY, 0.0, 0.0, datetime.now(), 0, 100),
            "meeting_scheduling": FeatureHealth("meeting_scheduling", FeatureStatus.HEALTHY, 0.0, 0.0, datetime.now(), 0, 20),
            "email_settings": FeatureHealth("email_settings", FeatureStatus.HEALTHY, 0.0, 0.0, datetime.now(), 0, 100)
        }
        
        # System resource monitoring
        self.system_metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "active_connections": 0
        }
        
        # Rate limiting per user
        self.user_rate_limits: Dict[int, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=100)))
        
        # Cleanup task
        self._cleanup_task = None
        self._monitoring_task = None
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        # Don't start the tasks during module import
        # They will be started when the application starts
        self._cleanup_task = None
        self._monitoring_task = None
    
    async def _cleanup_loop(self):
        """Background cleanup of inactive sessions"""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                await self._cleanup_inactive_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                monitoring_logger.error(f"User monitor cleanup error: {e}")
    
    async def _monitoring_loop(self):
        """Background system monitoring"""
        while True:
            try:
                await asyncio.sleep(30)  # Monitor every 30 seconds
                await self._update_system_metrics()
                await self._check_feature_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                monitoring_logger.error(f"User monitor error: {e}")
    
    async def _cleanup_inactive_sessions(self):
        """Remove inactive user sessions"""
        current_time = datetime.now()
        inactive_threshold = timedelta(minutes=30)
        
        inactive_users = []
        for user_id, session in self.active_sessions.items():
            if current_time - session.last_activity > inactive_threshold:
                inactive_users.append(user_id)
        
        for user_id in inactive_users:
            del self.active_sessions[user_id]
            monitoring_logger.info(f"Cleaned up inactive session for user {user_id}")
    
    async def _update_system_metrics(self):
        """Update system resource metrics"""
        try:
            self.system_metrics["cpu_usage"] = psutil.cpu_percent(interval=1)
            self.system_metrics["memory_usage"] = psutil.virtual_memory().percent
            self.system_metrics["disk_usage"] = psutil.disk_usage('/').percent
            self.system_metrics["active_connections"] = len(self.active_sessions)
        except Exception as e:
            monitoring_logger.error(f"Failed to update system metrics: {e}")
    
    async def _check_feature_health(self):
        """Check health of all features"""
        for feature_name, health in self.feature_health.items():
            # Update user count
            health.user_count = sum(1 for session in self.active_sessions.values() 
                                  if feature_name in session.features_used)
            
            # Check if feature is overloaded
            if health.user_count > health.max_capacity:
                health.status = FeatureStatus.DEGRADED
                monitoring_logger.warning(f"Feature {feature_name} is overloaded: {health.user_count}/{health.max_capacity}")
            elif health.user_count > health.max_capacity * 0.8:
                health.status = FeatureStatus.DEGRADED
                monitoring_logger.warning(f"Feature {feature_name} is approaching capacity: {health.user_count}/{health.max_capacity}")
            else:
                health.status = FeatureStatus.HEALTHY
    
    def track_user_activity(self, user_id: int, email: str, feature: str, ip_address: str):
        """Track user activity and update session"""
        current_time = datetime.now()
        
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = UserSession(
                user_id=user_id,
                email=email,
                last_activity=current_time,
                request_count=1,
                status=UserStatus.ACTIVE,
                features_used=set([feature]),
                ip_address=ip_address,
                session_start=current_time
            )
        else:
            session = self.active_sessions[user_id]
            session.last_activity = current_time
            session.request_count += 1
            session.features_used.add(feature)
        
        # Track activity for rate limiting
        self.user_activity[user_id].append(current_time)
        
        # Update feature usage
        if feature in self.feature_health:
            self.feature_health[feature].user_count = len([
                s for s in self.active_sessions.values() 
                if feature in s.features_used
            ])
    
    def check_user_rate_limit(self, user_id: int, feature: str, limit: int = 50, window: int = 300) -> bool:
        """Check if user has exceeded rate limit for a feature"""
        current_time = time.time()
        window_start = current_time - window
        
        # Get user's requests for this feature
        user_requests = self.user_rate_limits[user_id][feature]
        
        # Remove old requests outside the window
        while user_requests and user_requests[0] < window_start:
            user_requests.popleft()
        
        # Check if limit exceeded
        if len(user_requests) >= limit:
            return False
        
        # Add current request
        user_requests.append(current_time)
        return True
    
    def get_user_status(self, user_id: int) -> Optional[UserSession]:
        """Get current user session status"""
        return self.active_sessions.get(user_id)
    
    def get_feature_status(self, feature: str) -> Optional[FeatureHealth]:
        """Get current feature health status"""
        return self.feature_health.get(feature)
    
    def get_system_status(self) -> Dict:
        """Get overall system status"""
        return {
            "active_users": len(self.active_sessions),
            "system_metrics": self.system_metrics,
            "feature_health": {name: {
                "status": health.status,
                "user_count": health.user_count,
                "max_capacity": health.max_capacity,
                "response_time": health.response_time,
                "error_rate": health.error_rate
            } for name, health in self.feature_health.items()},
            "timestamp": datetime.now().isoformat()
        }
    
    def block_user(self, user_id: int, reason: str = "Rate limit exceeded"):
        """Block a user from accessing features"""
        if user_id in self.active_sessions:
            self.active_sessions[user_id].status = UserStatus.BLOCKED
            monitoring_logger.warning(f"Blocked user {user_id}: {reason}")
    
    def unblock_user(self, user_id: int):
        """Unblock a user"""
        if user_id in self.active_sessions:
            self.active_sessions[user_id].status = UserStatus.ACTIVE
            monitoring_logger.info(f"Unblocked user {user_id}")

# Global instance
user_monitor = UserMonitor()
