from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class Task(BaseModel):
    id: str
    worker: str = Field(..., description="wolfy, communicator, or manager")
    action: str
    input_data: Dict[str, Any]
    dependencies: List[str] = []
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None

class Plan(BaseModel):
    goal: str
    tasks: List[Task]
    metadata: Dict[str, Any] = {}

class AuditResult(BaseModel):
    is_valid: bool
    feedback: Optional[str] = None
    suggested_changes: Optional[List[str]] = None

