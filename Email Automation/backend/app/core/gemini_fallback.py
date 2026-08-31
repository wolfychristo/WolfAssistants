from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime
from app.core.gemini_cache import response_cache

class GeminiFallbackSystem:
    """Provides fallback responses when Gemini API is unavailable or rate limited."""

    def __init__(self):
        self._rule_based_responses = {
            'email_generation': self._generate_email_fallback,
            'chat_response': self._generate_chat_fallback,
            'intent_parsing': self._generate_intent_fallback,
            'web_research': self._generate_research_fallback
        }

    async def get_fallback_response(self, endpoint: str, request_type: str, context: Dict[str, Any]) -> Optional[str]:
        """Get a fallback response for the given endpoint and context."""
        if endpoint in self._rule_based_responses:
            fallback_func = self._rule_based_responses[endpoint]
            return await fallback_func(request_type, context)

        # Try to get similar cached responses as fallback
        return await self._get_cached_fallback(context)

    async def _generate_email_fallback(self, request_type: str, context: Dict[str, Any]) -> str:
        """Generate a fallback email response."""
        topic = context.get('topic', 'your request')
        recipient_name = context.get('recipient_name', 'there')
        user_name = context.get('user_name', 'User')

        if request_type == 'reply':
            return f"Hi {recipient_name},\n\nThank you for your email. I wanted to follow up on {topic}.\n\nBest regards,\n{user_name}"
        else:
            return f"Hi {recipient_name},\n\nI hope this email finds you well. I wanted to discuss {topic} with you.\n\nBest regards,\n{user_name}"

    async def _generate_chat_fallback(self, request_type: str, context: Dict[str, Any]) -> str:
        """Generate a fallback chat response."""
        message = context.get('message', '')

        # Analyze message for common patterns
        message_lower = message.lower()

        if any(word in message_lower for word in ['thank', 'thanks']):
            return "You're welcome! I'm here to help you with anything else you need."

        elif any(word in message_lower for word in ['help', 'assist', 'support']):
            return "I'm here to help! You can ask me about:\n\n• Email composition and sending\n• Meeting scheduling\n• Contact management\n• Inbox checking\n\nWhat would you like to do?"

        elif any(word in message_lower for word in ['meeting', 'schedule', 'appointment']):
            return "I can help you schedule a meeting! Please provide:\n\n• Meeting title/purpose\n• Date and time\n• Attendee email addresses\n• Duration (optional)\n\nFor example: 'Schedule a meeting with john@example.com tomorrow at 2 PM for project discussion'"

        elif any(word in message_lower for word in ['email', 'send', 'compose']):
            return "I can help you compose and send emails! Please provide:\n\n• Recipient email address\n• Subject (optional)\n• Message content\n\nFor example: 'Send email to jane@example.com about quarterly review'"

        else:
            return "I understand you're asking about something. While my AI capabilities are temporarily limited, I can help you with:\n\n• Composing and sending emails\n• Scheduling meetings\n• Managing your contacts\n• Checking your inbox\n\nPlease let me know what you'd like to do!"

    async def _generate_intent_fallback(self, request_type: str, context: Dict[str, Any]) -> str:
        """Generate a fallback intent analysis."""
        message = context.get('message', '')

        # Simple rule-based intent detection
        message_lower = message.lower()

        if 'send' in message_lower and 'email' in message_lower:
            return 'send_email'
        elif 'schedule' in message_lower or 'meeting' in message_lower:
            return 'schedule_meeting'
        elif 'check' in message_lower and 'inbox' in message_lower:
            return 'check_inbox'
        elif 'research' in message_lower or 'search' in message_lower:
            return 'web_research'
        else:
            return 'chat'

    async def _generate_research_fallback(self, request_type: str, context: Dict[str, Any]) -> str:
        """Generate a fallback research response."""
        query = context.get('query', '')

        return f"I can help you research '{query}'. While my AI capabilities are temporarily limited, I can:\n\n• Search for recent news and articles\n• Find company information\n• Look up industry trends\n\nPlease try again in a few minutes when the service is restored."

    async def _get_cached_fallback(self, context: Dict[str, Any]) -> Optional[str]:
        """Get similar cached responses as fallback."""
        try:
            similar_responses = await response_cache.get_similar_responses(context, limit=3)

            if similar_responses:
                # Return the most recent similar response
                return similar_responses[0]['response']
        except Exception:
            pass

        return None

    def get_status_message(self, error_type: str) -> str:
        """Get user-friendly status message for different error types."""
        messages = {
            'rate_limit': "I'm currently experiencing high demand. Please try again in a few minutes.",
            'quota_exceeded': "Daily usage limit reached. The service will be available again tomorrow.",
            'api_error': "I'm having technical difficulties. Please try again in a few minutes.",
            'no_api_key': "AI service is not configured. Please contact support.",
            'cache_fallback': "Using previously generated response due to high demand.",
            'rule_based': "AI service temporarily unavailable, using standard responses."
        }

        return messages.get(error_type, "Service temporarily unavailable. Please try again later.")

# Global fallback system instance
fallback_system = GeminiFallbackSystem()
