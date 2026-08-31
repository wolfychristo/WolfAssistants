from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel
from ..context import StateContext
from ..models import ToolInput, ToolOutput

class BaseWorker(ABC):
    """Base class for all worker tools with Input/Output schema support."""
    
    @property
    def description(self) -> str:
        """Human-readable description of this worker."""
        return "A worker tool"
    
    @property
    def supported_actions(self) -> list:
        """List of action names this worker supports."""
        return []
    
    @property
    def input_schema(self) -> Optional[Type[ToolInput]]:
        """Pydantic schema for input validation (optional)."""
        return None
    
    @property
    def output_schema(self) -> Optional[Type[ToolOutput]]:
        """Pydantic schema for output validation (optional)."""
        return None
    
    @abstractmethod
    async def run(self, action: str, input_data: Dict[str, Any], context: StateContext) -> Any:
        """
        Execute a specific action with the given input data and context.
        
        Args:
            action: The action to perform
            input_data: Input parameters (should match input_schema if defined)
            context: Shared state context
            
        Returns:
            Result of the action (should match output_schema if defined)
        """
        pass

