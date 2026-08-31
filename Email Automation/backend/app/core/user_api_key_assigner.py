"""
User API Key Assigner
Assigns API keys to users based on engagement level and tier
"""

from typing import Optional, Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from app.models.user import User
from app.models.email import Email, EmailStatus
from app.core.config import settings
from app.core.gemini_key_manager import key_manager, KeyStatus

logger = logging.getLogger(__name__)


class UserAPIKeyAssigner:
    """Assigns API keys to users based on engagement and tier"""
    
    # Key categories mapped to engagement levels
    KEY_CATEGORIES = {
        'enterprise': [0, 1],      # Keys 1-2 (indices 0-1)
        'professional': [2, 3],    # Keys 3-4 (indices 2-3)
        'starter': [4, 5],         # Keys 5-6 (indices 4-5)
        'free': [6, 7]            # Keys 7-8 (indices 6-7)
    }
    
    def __init__(self):
        self.all_keys = settings.gemini_api_keys
        self._key_usage: Dict[str, int] = {}  # Track usage per key
        self._category_usage: Dict[str, int] = {}  # Track usage per category
    
    def get_user_category(self, user: User, db: Session) -> str:
        """
        Determine user category based on tier and engagement
        Returns: 'enterprise', 'professional', 'starter', or 'free'
        """
        # Get user tier
        pricing_tier = getattr(user, 'pricing_tier', 'free')
        
        # Get email activity in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        try:
            emails_sent = db.query(func.count(Email.id)).filter(
                Email.owner_email == user.email,
                Email.status == EmailStatus.sent,
                Email.sent_at >= thirty_days_ago
            ).scalar() or 0
        except Exception as e:
            logger.warning(f"Error calculating email count for user {user.email}: {e}")
            emails_sent = 0
        
        # Categorize based on tier and activity
        if pricing_tier == 'enterprise' or emails_sent >= 1000:
            return 'enterprise'
        elif pricing_tier == 'professional' or emails_sent >= 100:
            return 'professional'
        elif pricing_tier == 'starter' or emails_sent >= 10:
            return 'starter'
        else:
            return 'free'
    
    def _get_category_keys(self, category: str) -> List[str]:
        """Get available keys for a category"""
        key_indices = self.KEY_CATEGORIES.get(category, self.KEY_CATEGORIES['free'])
        category_keys = [self.all_keys[i] for i in key_indices if i < len(self.all_keys)]
        
        if not category_keys:
            # Fallback to all keys if category keys not available
            category_keys = self.all_keys
        
        return category_keys
    
    def _select_best_key(self, keys: List[str]) -> Optional[str]:
        """
        Select best key based on health score, usage, and rate limits
        """
        if not keys:
            return None
        
        scored_keys = []
        for key in keys:
            health = key_manager.key_health.get(key)
            if not health or health.status == KeyStatus.UNHEALTHY:
                continue
            
            # Calculate composite score
            usage_score = 1.0 / (self._key_usage.get(key, 0) + 1)
            health_score = 1.0 if health.status == KeyStatus.HEALTHY else 0.5
            rate_limit_score = min(health.rate_limit_remaining / 60.0, 1.0)
            
            composite_score = (
                usage_score * 0.3 + 
                health_score * 0.4 + 
                rate_limit_score * 0.3
            )
            
            scored_keys.append((composite_score, key))
        
        if not scored_keys:
            return None
        
        # Return key with highest score
        scored_keys.sort(reverse=True)
        return scored_keys[0][1]
    
    def _try_overflow(self, category: str, primary_keys: List[str]) -> Optional[str]:
        """
        Try to use keys from adjacent categories when primary is overloaded
        """
        # Define overflow hierarchy
        overflow_map = {
            'enterprise': ['professional'],
            'professional': ['enterprise', 'starter'],
            'starter': ['professional', 'free'],
            'free': ['starter']
        }
        
        overflow_categories = overflow_map.get(category, [])
        
        for overflow_cat in overflow_categories:
            overflow_keys = self._get_category_keys(overflow_cat)
            # Filter to healthy keys
            healthy_overflow = [
                k for k in overflow_keys
                if key_manager.key_health.get(k) and 
                key_manager.key_health[k].status in [KeyStatus.HEALTHY, KeyStatus.DEGRADED]
            ]
            
            if healthy_overflow:
                selected = self._select_best_key(healthy_overflow)
                if selected:
                    # Track overflow usage
                    self._category_usage[f"{category}_overflow"] = \
                        self._category_usage.get(f"{category}_overflow", 0) + 1
                    logger.info(f"Overflow: {category} -> {overflow_cat} for key selection")
                    return selected
        
        return None
    
    def get_api_key_for_user(
        self, 
        user_email: str, 
        db: Session,
        fallback_to_other_categories: bool = True
    ) -> Optional[str]:
        """
        Get the appropriate API key for a user based on their category
        Uses intelligent selection with fallback support
        """
        if not self.all_keys:
            return None
        
        # Get user from accounts database (User model is in accounts DB, not tenant DB)
        user = None
        try:
            from app.core.database import AccountsSessionLocal
            accounts_db = AccountsSessionLocal()
            try:
                user = accounts_db.query(User).filter(User.email == user_email).first()
            except Exception as e:
                logger.warning(f"Error querying user from accounts database: {e}, defaulting to free tier")
                user = None
            finally:
                accounts_db.close()
        except Exception as e:
            logger.warning(f"Failed to get accounts database session: {e}, defaulting to free tier")
            user = None
        
        if not user:
            # Default to free tier for unknown users
            category = 'free'
        else:
            try:
                category = self.get_user_category(user, db)
            except Exception as e:
                logger.warning(f"Error determining user category: {e}, defaulting to free tier")
                category = 'free'
        
        # Get available keys for this category
        category_keys = self._get_category_keys(category)
        
        if not category_keys:
            return None
        
        # Filter to healthy keys
        healthy_keys = [
            k for k in category_keys
            if key_manager.key_health.get(k) and 
            key_manager.key_health[k].status in [KeyStatus.HEALTHY, KeyStatus.DEGRADED]
        ]
        
        # If no healthy keys in category, try overflow
        if not healthy_keys and fallback_to_other_categories:
            selected_key = self._try_overflow(category, category_keys)
            if selected_key:
                self._key_usage[selected_key] = self._key_usage.get(selected_key, 0) + 1
                return selected_key
        
        # Use any available if still no healthy keys
        if not healthy_keys:
            healthy_keys = category_keys
        
        # Select best key from primary category
        selected_key = self._select_best_key(healthy_keys)
        
        if selected_key:
            self._key_usage[selected_key] = self._key_usage.get(selected_key, 0) + 1
            self._category_usage[category] = self._category_usage.get(category, 0) + 1
        elif fallback_to_other_categories:
            # Last resort: try overflow
            selected_key = self._try_overflow(category, category_keys)
            if selected_key:
                self._key_usage[selected_key] = self._key_usage.get(selected_key, 0) + 1
        
        return selected_key
    
    def get_category_stats(self, db: Session) -> Dict[str, Dict]:
        """Get statistics about key usage by category"""
        stats = {}
        
        for category, key_indices in self.KEY_CATEGORIES.items():
            category_keys = [self.all_keys[i] for i in key_indices if i < len(self.all_keys)]
            total_usage = sum(self._key_usage.get(key, 0) for key in category_keys)
            
            # Count healthy keys
            healthy_count = sum(
                1 for key in category_keys
                if key_manager.key_health.get(key) and 
                key_manager.key_health[key].status in [KeyStatus.HEALTHY, KeyStatus.DEGRADED]
            )
            
            stats[category] = {
                'keys': len(category_keys),
                'healthy_keys': healthy_count,
                'key_indices': key_indices,
                'total_usage': total_usage,
                'category_usage': self._category_usage.get(category, 0),
                'avg_usage_per_key': total_usage / len(category_keys) if category_keys else 0,
                'overflow_usage': self._category_usage.get(f"{category}_overflow", 0)
            }
        
        return stats


# Global instance
user_key_assigner = UserAPIKeyAssigner()

