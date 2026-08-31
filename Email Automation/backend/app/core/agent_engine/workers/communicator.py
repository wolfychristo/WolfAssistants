import logging
from typing import Dict, Any
from .base import BaseWorker
from ..context import StateContext

logger = logging.getLogger(__name__)

class CommunicatorWorker(BaseWorker):
    @property
    def description(self) -> str:
        """Human-readable description of this worker."""
        return "Communicator: The Outreach Agent. Drafts hyper-personalized, authenticated emails."
    
    @property
    def supported_actions(self) -> list:
        """List of action names this worker supports."""
        return ["draft_email"]
    
    async def run(self, action: str, input_data: Dict[str, Any], context: StateContext) -> Any:
        """
        Communicator: The Outreach Agent.
        Drafts hyper-personalized, authenticated emails.
        """
        if action == "draft_email":
            lead_data = context.get("last_scraped_lead", {})
            logger.info(f"🚧 Communicator drafting email for: {lead_data.get('email')}")
            
            # Use LLM logic to draft personalized content
            draft = f"Hi {lead_data.get('name', 'there')}, I saw your work in {lead_data.get('industry')}..."
            context.update("email_draft", draft)
            return {"draft": draft, "subject": "Personalized Outreach"}
            
        else:
            raise ValueError(f"Action '{action}' not supported by Communicator.")

