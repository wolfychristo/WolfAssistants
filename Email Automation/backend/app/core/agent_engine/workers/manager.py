import logging
from typing import Dict, Any
from .base import BaseWorker
from ..context import StateContext

logger = logging.getLogger(__name__)

class ManagerWorker(BaseWorker):
    @property
    def description(self) -> str:
        """Human-readable description of this worker."""
        return "Manager: The Operational Agent. Handles meetings and local state (To-Dos)."
    
    @property
    def supported_actions(self) -> list:
        """List of action names this worker supports."""
        return ["schedule_meeting", "create_todo"]
    
    async def run(self, action: str, input_data: Dict[str, Any], context: StateContext) -> Any:
        """
        Manager: The Operational Agent.
        Handles meetings and local state (To-Dos).
        """
        if action == "schedule_meeting":
            time = input_data.get("time")
            logger.info(f"🚧 Manager scheduling meeting at: {time}")
            # Real implementation would interact with Google/Outlook Calendar
            result = {"status": "scheduled", "link": "zoom.us/j/123456"}
            context.update("last_meeting", result)
            return result
            
        elif action == "create_todo":
            task = input_data.get("task")
            logger.info(f"🚧 Manager creating To-Do: {task}")
            # Real implementation would add to local DB
            return {"status": "created", "id": "todo_123"}
            
        else:
            raise ValueError(f"Action '{action}' not supported by Manager.")

