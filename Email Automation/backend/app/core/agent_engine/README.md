# WolfAssistants Agentic Engine

A modular AI Orchestration Framework implementing a **Plan-Execute-Review** loop for orchestrating multiple specialized AI workers.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WolfOrchestrator                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│  │ Planner  │──▶ │ Registry │──▶│  Critic  │              |
│  └──────────┘    └──────────┘    └──────────┘               │
│       │              │                │                     │
│       ▼              ▼                ▼                     │
│  ┌──────────────────────────────────────────┐               │
│  │         StateContext (Shared Memory)      │              │
│  └──────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Worker Tools        │
              │  - Wolfy              │
              │  - Communicator       │
              │  - Manager            │
              └───────────────────────┘
```

## Core Components

### 1. **WolfOrchestrator** (`wolf_orchestrator.py`)
The main orchestrator that coordinates the Plan-Execute-Review loop.

**Key Features:**
- Decomposes user goals into task sequences
- Executes tasks with automatic retry logic
- Reviews results against original intent
- Returns structured `AgentResponse` objects

**Usage:**
```python
from app.core.agent_engine import WolfOrchestrator

orchestrator = WolfOrchestrator(model="gemini/gemini-pro")
response = await orchestrator.execute(
    goal="Scrape example.com and draft an email",
    max_retries=2,
    enable_review=True
)
```

### 2. **Models** (`models.py`)
Pydantic schemas for type-safe data validation.

**Key Schemas:**
- `Task`: Individual task in execution plan
- `Plan`: Complete execution plan with multiple tasks
- `AgentResponse`: Final response from orchestrator
- `AuditResult`: Review/audit results
- `ToolInput` / `ToolOutput`: Base classes for tool schemas

### 3. **WorkerRegistry** (`registry.py`)
Enhanced tool registry with metadata and lookup capabilities.

**Features:**
- Register workers with descriptions and supported actions
- Input/Output schema validation
- Action-to-worker mapping
- Worker metadata lookup

**Usage:**
```python
registry.register(
    name="wolfy",
    worker_instance=WolfyWorker(),
    description="Scrapes and enriches lead data",
    supported_actions=["scrape_website", "enrich_contact"],
    input_schema=ScrapeWebsiteInput,  # Optional
    output_schema=ScrapeWebsiteOutput  # Optional
)
```

### 4. **StateContext** (`context.py`)
Enhanced state manager with namespacing and history tracking.

**Features:**
- Key-value storage for inter-task communication
- Namespace support for organizing variables
- History tracking for debugging
- Thread-safe operations

**Usage:**
```python
context.update("last_scraped_lead", lead_data)
context.update("email_draft", draft, namespace="communicator")
lead = context.get("last_scraped_lead")
```

### 5. **Planner** (`planner.py`)
Uses LiteLLM to decompose goals into task sequences.

**Features:**
- LLM-powered goal decomposition
- JSON-validated task generation
- Dependency resolution

### 6. **Critic** (`critic.py`)
Reviews execution results against original intent.

**Features:**
- LLM-powered quality control
- Brand voice validation
- Alignment checking
- Feedback generation

## Creating Custom Workers

### Step 1: Create Worker Class

```python
from app.core.agent_engine.workers.base import BaseWorker
from app.core.agent_engine.context import StateContext
from typing import Dict, Any

class MyCustomWorker(BaseWorker):
    @property
    def description(self) -> str:
        return "My custom worker description"
    
    @property
    def supported_actions(self) -> list:
        return ["action1", "action2"]
    
    async def run(
        self,
        action: str,
        input_data: Dict[str, Any],
        context: StateContext
    ) -> Any:
        if action == "action1":
            # Implementation
            result = {"status": "success"}
            context.update("my_result", result)
            return result
        else:
            raise ValueError(f"Action '{action}' not supported")
```

### Step 2: Register Worker

```python
orchestrator.register_worker(
    name="my_worker",
    worker_instance=MyCustomWorker(),
    description="My custom worker",
    supported_actions=["action1", "action2"]
)
```

### Step 3: (Optional) Add Input/Output Schemas

```python
from app.core.agent_engine.models import ToolInput, ToolOutput
from pydantic import Field

class MyActionInput(ToolInput):
    url: str = Field(..., description="URL to process")
    timeout: int = Field(30, description="Timeout in seconds")

class MyActionOutput(ToolOutput):
    data: Dict[str, Any] = Field(..., description="Processed data")
    status_code: int = Field(..., description="HTTP status code")

# Register with schemas
orchestrator.register_worker(
    name="my_worker",
    worker_instance=MyCustomWorker(),
    input_schema=MyActionInput,
    output_schema=MyActionOutput
)
```

## Execution Flow

1. **PLAN Phase**
   - User provides a goal
   - Planner decomposes goal into tasks
   - Tasks are validated and dependencies resolved

2. **EXECUTE Phase**
   - Tasks executed in order (respecting dependencies)
   - Each task runs through a worker
   - Results stored in StateContext
   - Automatic retry on failure

3. **REVIEW Phase**
   - Critic audits final results
   - Checks alignment with original goal
   - Validates brand voice and quality
   - Returns feedback and suggestions

## Error Handling

- **Task Failures**: Automatic retry with exponential backoff
- **Validation Errors**: Input/Output schema validation catches errors early
- **Worker Not Found**: Clear error messages with suggestions
- **Dependency Failures**: Tasks with unmet dependencies are skipped

## Best Practices

1. **Use Type Hints**: Always use Pydantic schemas for Input/Output
2. **Update Context**: Store intermediate results in StateContext
3. **Handle Errors**: Return structured error information
4. **Document Actions**: Provide clear descriptions for workers
5. **Test Workers**: Test each worker independently before integration

## Example: Complete Workflow

```python
import asyncio
from app.core.agent_engine import WolfOrchestrator
from app.core.agent_engine.workers.wolfy import WolfyWorker
from app.core.agent_engine.workers.communicator import CommunicatorWorker

async def main():
    # Initialize
    orchestrator = WolfOrchestrator()
    
    # Register workers
    orchestrator.register_worker(
        name="wolfy",
        worker_instance=WolfyWorker(),
        description=WolfyWorker().description,
        supported_actions=WolfyWorker().supported_actions
    )
    
    # Execute goal
    response = await orchestrator.execute(
        goal="Scrape example.com and draft an email",
        max_retries=2,
        enable_review=True
    )
    
    # Handle response
    if response.success:
        print(f"✅ Success: {response.final_result}")
    else:
        print(f"❌ Errors: {response.errors}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Migration from Old System

The old `schemas.py` is still available for backward compatibility. New code should use `models.py`:

- `from .schemas import Plan` → `from .models import Plan`
- `from .schemas import Task` → `from .models import Task`

The `AgenticEngine` class still works but `WolfOrchestrator` is recommended for new code.

