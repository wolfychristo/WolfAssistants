from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Type
from enum import Enum
from datetime import datetime

# ============================================================================
# Task & Plan Schemas
# ============================================================================

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"

class Task(BaseModel):
    """A single task in the execution plan."""
    id: str = Field(..., description="Unique task identifier")
    worker: str = Field(..., description="Worker name (e.g., 'wolfy', 'communicator', 'manager')")
    action: str = Field(..., description="Action to perform (e.g., 'scrape_website', 'draft_email')")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input parameters for the action")
    dependencies: List[str] = Field(default_factory=list, description="Task IDs that must complete first")
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class Plan(BaseModel):
    """A complete execution plan with multiple tasks."""
    goal: str = Field(..., description="Original user goal")
    tasks: List[Task] = Field(default_factory=list, description="Ordered list of tasks")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional plan metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ============================================================================
# Tool Input/Output Schemas
# ============================================================================

class ToolInput(BaseModel):
    """Base class for tool input schemas."""
    pass

class ToolOutput(BaseModel):
    """Base class for tool output schemas."""
    success: bool = Field(default=True, description="Whether the tool execution succeeded")
    error: Optional[str] = Field(None, description="Error message if execution failed")

# ============================================================================
# Agent Response Schema
# ============================================================================

class AuditResult(BaseModel):
    """Result from the Review/Critic step."""
    is_valid: bool = Field(..., description="Whether the output matches user intent")
    feedback: Optional[str] = Field(None, description="Detailed feedback")
    suggested_changes: Optional[List[str]] = Field(None, description="Suggested improvements")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence in the result")

class AgentResponse(BaseModel):
    """Final response from the orchestrator."""
    goal: str = Field(..., description="Original user goal")
    success: bool = Field(..., description="Whether the goal was accomplished")
    plan: Optional[Plan] = Field(None, description="The execution plan that was followed")
    final_result: Optional[Any] = Field(None, description="Final output/result")
    audit_result: Optional[AuditResult] = Field(None, description="Review/audit results")
    execution_time_seconds: Optional[float] = Field(None, description="Total execution time")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")

