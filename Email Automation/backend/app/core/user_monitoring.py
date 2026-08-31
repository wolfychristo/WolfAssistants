"""
User Activity Monitoring and Abuse Detection Service
"""
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.user import User
from app.models.user_activity import (
    UserActivity, UserBan, AbusePattern, AdminNotification,
    ActivityType, BanReason, BanStatus
)

class UserMonitoringService:
    """Service for monitoring user activities and detecting abuse patterns"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_activity(
        self,
        user_id: int,
        activity_type: ActivityType,
        description: str = None,
        ip_address: str = None,
        user_agent: str = None,
        metadata: Dict[str, Any] = None,
        risk_score: int = 0
    ) -> UserActivity:
        """Log a user activity"""
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            activity_metadata=json.dumps(metadata) if metadata else None,
            risk_score=risk_score
        )
        
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        
        # Check for abuse patterns after logging
        self._check_abuse_patterns(user_id, activity)
        
        return activity
    
    def _check_abuse_patterns(self, user_id: int, activity: UserActivity):
        """Check for abuse patterns and trigger alerts if needed"""
        patterns = self._detect_abuse_patterns(user_id, activity)
        
        for pattern in patterns:
            self._handle_abuse_pattern(user_id, pattern)
    
    def _detect_abuse_patterns(self, user_id: int, activity: UserActivity) -> List[Dict[str, Any]]:
        """Detect various abuse patterns"""
        patterns = []
        
        # Check for rapid email sending
        if activity.activity_type == ActivityType.EMAIL_SENT:
            rapid_sending = self._check_rapid_email_sending(user_id)
            if rapid_sending:
                patterns.append(rapid_sending)
        
        # Check for spam keywords
        if activity.activity_type in [ActivityType.EMAIL_SENT, ActivityType.CONTACT_CREATED]:
            spam_detection = self._check_spam_keywords(user_id, activity)
            if spam_detection:
                patterns.append(spam_detection)
        
        # Check for suspicious login patterns
        if activity.activity_type == ActivityType.LOGIN:
            suspicious_login = self._check_suspicious_login(user_id, activity)
            if suspicious_login:
                patterns.append(suspicious_login)
        
        # Check for API abuse
        if activity.activity_type == ActivityType.API_ABUSE:
            api_abuse = self._check_api_abuse(user_id)
            if api_abuse:
                patterns.append(api_abuse)
        
        return patterns
    
    def _check_rapid_email_sending(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Check for rapid email sending (potential spam)"""
        # Check emails sent in last 5 minutes
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        
        recent_emails = self.db.query(UserActivity).filter(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.activity_type == ActivityType.EMAIL_SENT,
                UserActivity.created_at >= five_minutes_ago
            )
        ).count()
        
        if recent_emails >= 10:  # 10+ emails in 5 minutes
            return {
                "type": "rapid_email_sending",
                "severity": 4,
                "description": f"User sent {recent_emails} emails in 5 minutes",
                "threshold": 10,
                "actual": recent_emails
            }
        
        return None
    
    def _check_spam_keywords(self, user_id: int, activity: UserActivity) -> Optional[Dict[str, Any]]:
        """Check for spam keywords in email content"""
        spam_keywords = [
            "free money", "get rich quick", "click here", "limited time",
            "act now", "guaranteed", "no risk", "make money fast",
            "work from home", "earn cash", "investment opportunity"
        ]
        
        if activity.activity_metadata:
            try:
                metadata = json.loads(activity.activity_metadata)
                content = (metadata.get("subject", "") + " " + metadata.get("body", "")).lower()
                
                found_keywords = [keyword for keyword in spam_keywords if keyword in content]
                
                if found_keywords:
                    return {
                        "type": "spam_keywords",
                        "severity": 3,
                        "description": f"Spam keywords detected: {', '.join(found_keywords)}",
                        "keywords": found_keywords
                    }
            except (json.JSONDecodeError, KeyError):
                pass
        
        return None
    
    def _check_suspicious_login(self, user_id: int, activity: UserActivity) -> Optional[Dict[str, Any]]:
        """Check for suspicious login patterns"""
        # Check for multiple IP addresses in short time
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        recent_logins = self.db.query(UserActivity).filter(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.activity_type == ActivityType.LOGIN,
                UserActivity.created_at >= one_hour_ago
            )
        ).all()
        
        unique_ips = set(login.ip_address for login in recent_logins if login.ip_address)
        
        if len(unique_ips) >= 3:  # 3+ different IPs in 1 hour
            return {
                "type": "suspicious_login",
                "severity": 3,
                "description": f"Login from {len(unique_ips)} different IP addresses in 1 hour",
                "ip_addresses": list(unique_ips)
            }
        
        return None
    
    def _check_api_abuse(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Check for API abuse patterns"""
        # Check for excessive API calls
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        api_calls = self.db.query(UserActivity).filter(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.activity_type == ActivityType.API_ABUSE,
                UserActivity.created_at >= one_hour_ago
            )
        ).count()
        
        if api_calls >= 100:  # 100+ API abuse events in 1 hour
            return {
                "type": "api_abuse",
                "severity": 4,
                "description": f"Excessive API abuse: {api_calls} events in 1 hour",
                "threshold": 100,
                "actual": api_calls
            }
        
        return None
    
    def _handle_abuse_pattern(self, user_id: int, pattern: Dict[str, Any]):
        """Handle detected abuse patterns"""
        # Record the abuse pattern
        abuse_pattern = AbusePattern(
            user_id=user_id,
            pattern_type=pattern["type"],
            severity=pattern["severity"],
            occurrences=1
        )
        
        self.db.add(abuse_pattern)
        
        # Check if we should auto-ban
        if pattern["severity"] >= 4:
            self._consider_auto_ban(user_id, pattern)
        
        # Send notification to admins
        self._notify_admins(user_id, pattern)
        
        self.db.commit()
    
    def _consider_auto_ban(self, user_id: int, pattern: Dict[str, Any]):
        """Consider automatic banning for severe abuse"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.is_admin:
            return  # Don't auto-ban admins
        
        # Check if user already has recent bans
        recent_bans = self.db.query(UserBan).filter(
            and_(
                UserBan.user_id == user_id,
                UserBan.created_at >= datetime.utcnow() - timedelta(days=30)
            )
        ).count()
        
        if recent_bans >= 2:
            # Auto-ban for repeated offenses
            self._ban_user(
                user_id=user_id,
                banned_by=1,  # System admin
                reason=BanReason.SYSTEM_ABUSE,
                description=f"Auto-ban for repeated abuse: {pattern['description']}",
                ban_duration_days=7
            )
    
    def _notify_admins(self, user_id: int, pattern: Dict[str, Any]):
        """Send notification to admins about abuse detection"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        
        # Get all admin users
        admins = self.db.query(User).filter(User.is_admin == True).all()
        
        for admin in admins:
            notification = AdminNotification(
                notification_type="abuse_detected",
                title=f"Abuse Pattern Detected - {pattern['type']}",
                message=f"User {user.email} has triggered abuse detection: {pattern['description']}",
                user_id=user_id,
                admin_id=admin.id,
                priority=pattern["severity"],
                notification_metadata=json.dumps(pattern)
            )
            
            self.db.add(notification)
        
        self.db.commit()
    
    def ban_user(
        self,
        user_id: int,
        banned_by: int,
        reason: BanReason,
        description: str,
        ban_duration_days: Optional[int] = None
    ) -> UserBan:
        """Ban a user"""
        return self._ban_user(user_id, banned_by, reason, description, ban_duration_days)
    
    def _ban_user(
        self,
        user_id: int,
        banned_by: int,
        reason: BanReason,
        description: str,
        ban_duration_days: Optional[int] = None
    ) -> UserBan:
        """Internal method to ban a user"""
        expires_at = None
        if ban_duration_days:
            expires_at = datetime.utcnow() + timedelta(days=ban_duration_days)
        
        ban = UserBan(
            user_id=user_id,
            banned_by=banned_by,
            reason=reason,
            description=description,
            ban_duration_days=ban_duration_days,
            expires_at=expires_at
        )
        
        self.db.add(ban)
        
        # Deactivate user account
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_active = False
        
        # Notify admins
        self._notify_ban_action(user_id, banned_by, reason, description)
        
        self.db.commit()
        self.db.refresh(ban)
        
        return ban
    
    def _notify_ban_action(self, user_id: int, banned_by: int, reason: BanReason, description: str):
        """Notify admins about ban action"""
        user = self.db.query(User).filter(User.id == user_id).first()
        banned_by_user = self.db.query(User).filter(User.id == banned_by).first()
        
        if not user or not banned_by_user:
            return
        
        # Get all admin users
        admins = self.db.query(User).filter(User.is_admin == True).all()
        
        for admin in admins:
            notification = AdminNotification(
                notification_type="user_banned",
                title=f"User Banned - {user.email}",
                message=f"User {user.email} has been banned by {banned_by_user.email}. Reason: {reason.value}. Details: {description}",
                user_id=user_id,
                admin_id=admin.id,
                priority=5,  # High priority
                notification_metadata=json.dumps({
                    "reason": reason.value,
                    "description": description,
                    "banned_by": banned_by_user.email
                })
            )
            
            self.db.add(notification)
        
        self.db.commit()
    
    def unban_user(self, user_id: int, unbanned_by: int, reason: str) -> bool:
        """Unban a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Get active ban
        active_ban = user.get_active_ban()
        if not active_ban:
            return False
        
        # Update ban status
        active_ban.status = BanStatus.OVERTURNED
        active_ban.updated_at = datetime.utcnow()
        
        # Reactivate user account
        user.is_active = True
        
        # Notify admins
        self._notify_unban_action(user_id, unbanned_by, reason)
        
        self.db.commit()
        return True
    
    def _notify_unban_action(self, user_id: int, unbanned_by: int, reason: str):
        """Notify admins about unban action"""
        user = self.db.query(User).filter(User.id == user_id).first()
        unbanned_by_user = self.db.query(User).filter(User.id == unbanned_by).first()
        
        if not user or not unbanned_by_user:
            return
        
        # Get all admin users
        admins = self.db.query(User).filter(User.is_admin == True).all()
        
        for admin in admins:
            notification = AdminNotification(
                notification_type="user_unbanned",
                title=f"User Unbanned - {user.email}",
                message=f"User {user.email} has been unbanned by {unbanned_by_user.email}. Reason: {reason}",
                user_id=user_id,
                admin_id=admin.id,
                priority=3,
                notification_metadata=json.dumps({
                    "reason": reason,
                    "unbanned_by": unbanned_by_user.email
                })
            )
            
            self.db.add(notification)
        
        self.db.commit()
    
    def get_user_risk_score(self, user_id: int) -> int:
        """Calculate overall risk score for a user"""
        # Get recent activities with risk scores
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        activities = self.db.query(UserActivity).filter(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.created_at >= thirty_days_ago
            )
        ).all()
        
        if not activities:
            return 0
        
        # Calculate weighted average risk score
        total_score = sum(activity.risk_score for activity in activities)
        return min(100, total_score // len(activities))
    
    def get_abuse_statistics(self) -> Dict[str, Any]:
        """Get abuse detection statistics"""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        stats = {
            "total_abuse_patterns": self.db.query(AbusePattern).filter(
                AbusePattern.created_at >= thirty_days_ago
            ).count(),
            "active_bans": self.db.query(UserBan).filter(
                UserBan.status == BanStatus.ACTIVE
            ).count(),
            "high_risk_users": self.db.query(User).filter(
                User.is_active == True
            ).count(),  # This would need a more sophisticated query
            "recent_notifications": self.db.query(AdminNotification).filter(
                AdminNotification.created_at >= thirty_days_ago
            ).count()
        }
        
        return stats
