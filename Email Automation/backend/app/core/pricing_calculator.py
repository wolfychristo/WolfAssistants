from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.core.gemini_service import gemini_service

class PricingCalculator:
    """Calculate pricing based on actual usage patterns."""

    # Base pricing tiers (USD per month)
    TIERS = {
        'starter': {
            'name': 'Starter',
            'price': 0,  # Free tier
            'limits': {
                'gemini_requests': 50,  # 50 Wolfy prompts per month
                'gemini_emails': 20,  # 20 emails using Gemini per month
                'contacts': 20,
                'meetings_per_month': 5
            },
            'features': ['Basic email automation', '20 emails using Gemini/month', '50 Wolfy prompts/month', 'Basic contact management']
        },
        'pro': {
            'name': 'Pro',
            'price': 29,  # Updated from $20 to $29
            'limits': {
                'gemini_requests': 2000,
                'emails_per_day': 200,
                'contacts': 1000,
                'meetings_per_month': 100
            },
            'features': ['Priority AI processing', '2000 AI requests/month', 'Advanced analytics', 'Team collaboration', 'API access', 'Meeting automation']
        },
        'enterprise': {
            'name': 'Enterprise',
            'price': 99,
            'limits': {
                'gemini_requests': 10000,
                'emails_per_day': 1000,
                'contacts': 5000,
                'meetings_per_month': 500
            },
            'features': ['Custom AI training', '10,000 AI requests/month', 'White-label options', 'Dedicated support', 'Custom integrations', 'SLA guarantees']
        }
    }
    
    # Legacy tier mapping (for backward compatibility)
    LEGACY_TIER_MAP = {
        'free': 'starter',
        'professional': 'pro'
    }

    # Cost per 1000 Gemini API requests (estimated)
    GEMINI_COST_PER_1000 = 0.50  # Conservative estimate

    def calculate_user_cost(self, user_email: str, days: int = 30) -> Dict[str, Any]:
        """Calculate actual cost of serving a user."""
        stats = gemini_service.get_usage_stats(user_email, days)

        # Calculate Gemini API costs
        gemini_requests = stats.get('total_requests', 0)
        gemini_cost = (gemini_requests / 1000) * self.GEMINI_COST_PER_1000

        # Infrastructure costs (estimated)
        infra_cost_per_user = 1.50  # Optimized shared infrastructure estimate per user

        # Support and maintenance (estimated)
        support_cost = 1.00  # Streamlined support cost per user

        total_cost = gemini_cost + infra_cost_per_user + support_cost

        return {
            'gemini_requests': gemini_requests,
            'gemini_cost': gemini_cost,
            'infrastructure_cost': infra_cost_per_user,
            'support_cost': support_cost,
        'total_cost': total_cost,
        'margin_at_starter': 0 - total_cost,  # Starter is free
        'margin_at_pro': 29 - total_cost
        }

    def recommend_tier(self, user_email: str, days: int = 30) -> str:
        """Recommend appropriate pricing tier based on usage."""
        cost_analysis = self.calculate_user_cost(user_email, days)

        if cost_analysis['total_cost'] > 99:
            return 'enterprise'
        elif cost_analysis['total_cost'] > 29:
            return 'pro'
        elif cost_analysis['total_cost'] > 0:
            return 'starter'
        else:
            return 'starter'
    

    def get_pricing_comparison(self) -> Dict[str, Any]:
        """Get comparison with competitors."""
        return {
            'competitors': {
                'mailchimp': {'basic': 13, 'standard': 20, 'premium': 350},
                'constant_contact': {'lite': 12, 'plus': 45, 'professional': 125},
                'sendinblue': {'free': 0, 'lite': 25, 'premium': 65},
                'brevo': {'free': 0, 'starter': 25, 'business': 65}
            },
            'our_positioning': 'Mid-tier with AI differentiation'
        }

# Global pricing calculator
pricing_calculator = PricingCalculator()
