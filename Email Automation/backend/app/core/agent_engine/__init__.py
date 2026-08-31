"""
WolfAssistants Agentic Engine - Modular AI Orchestration Framework

This package implements a Plan-Execute-Review loop for orchestrating
multiple specialized AI workers to accomplish complex goals.
"""

from .wolf_orchestrator import WolfOrchestrator
from .engine import AgenticEngine
from .models import (
    Task,
    Plan,
    TaskStatus,
    AgentResponse,
    AuditResult,
    ToolInput,
    ToolOutput
)
from .context import StateContext
from .registry import WorkerRegistry
from .planner import Planner
from .critic import Critic

__all__ = [
    "WolfOrchestrator",
    "AgenticEngine",
    "Task",
    "Plan",
    "TaskStatus",
    "AgentResponse",
    "AuditResult",
    "ToolInput",
    "ToolOutput",
    "StateContext",
    "WorkerRegistry",
    "Planner",
    "Critic",
]

