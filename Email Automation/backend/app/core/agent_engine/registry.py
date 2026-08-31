import logging
from typing import Dict, Any, Optional, Type, List
from .models import Task, TaskStatus, ToolInput, ToolOutput
from .context import StateContext

logger = logging.getLogger(__name__)

class ToolMetadata:
    """Metadata about a registered tool/worker."""
    def __init__(
        self,
        name: str,
        worker_instance: Any,
        description: str = "",
        input_schema: Optional[Type[ToolInput]] = None,
        output_schema: Optional[Type[ToolOutput]] = None,
        supported_actions: Optional[List[str]] = None
    ):
        self.name = name
        self.worker_instance = worker_instance
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.supported_actions = supported_actions or []

class WorkerRegistry:
    """Enhanced registry for managing and looking up worker tools."""
    
    def __init__(self):
        self._workers: Dict[str, ToolMetadata] = {}
        self._action_map: Dict[str, str] = {}  # Maps action -> worker_name

    def register(
        self,
        name: str,
        worker_instance: Any,
        description: str = "",
        input_schema: Optional[Type[ToolInput]] = None,
        output_schema: Optional[Type[ToolOutput]] = None,
        supported_actions: Optional[List[str]] = None
    ):
        """Register a worker tool with metadata."""
        metadata = ToolMetadata(
            name=name,
            worker_instance=worker_instance,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            supported_actions=supported_actions
        )
        
        self._workers[name] = metadata
        
        # Build action -> worker mapping
        if supported_actions:
            for action in supported_actions:
                self._action_map[action] = name
        
        logger.info(f"✅ [Registry] Registered worker: {name} (actions: {supported_actions})")

    def lookup_worker(self, worker_name: str) -> Optional[ToolMetadata]:
        """Lookup a worker by name."""
        return self._workers.get(worker_name)

    def lookup_by_action(self, action: str) -> Optional[ToolMetadata]:
        """Lookup a worker by action name."""
        worker_name = self._action_map.get(action)
        if worker_name:
            return self._workers.get(worker_name)
        return None

    def list_workers(self) -> List[str]:
        """List all registered worker names."""
        return list(self._workers.keys())

    def get_worker_info(self, worker_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata about a worker."""
        metadata = self._workers.get(worker_name)
        if not metadata:
            return None
        
        return {
            "name": metadata.name,
            "description": metadata.description,
            "supported_actions": metadata.supported_actions,
            "has_input_schema": metadata.input_schema is not None,
            "has_output_schema": metadata.output_schema is not None
        }

    async def execute_task(self, task: Task, context: StateContext) -> bool:
        """Dispatch and execute a single task with validation."""
        metadata = self.lookup_worker(task.worker)
        
        if not metadata:
            task.status = TaskStatus.FAILED
            task.error = f"Worker '{task.worker}' not found in registry."
            logger.error(f"⚠️ [Registry] {task.error}")
            return False

        # Validate input schema if provided
        if metadata.input_schema:
            try:
                validated_input = metadata.input_schema(**task.input_data)
                task.input_data = validated_input.dict()
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = f"Input validation failed: {str(e)}"
                logger.error(f"⚠️ [Registry] {task.error}")
                return False

        task.status = TaskStatus.RUNNING
        logger.info(f"🚧 [Registry] {task.worker.capitalize()} executing: {task.action}")

        try:
            # Execute the worker
            result = await metadata.worker_instance.run(
                task.action,
                task.input_data,
                context
            )
            
            # Validate output schema if provided
            if metadata.output_schema:
                try:
                    validated_output = metadata.output_schema(**result) if isinstance(result, dict) else result
                    task.result = validated_output.dict() if hasattr(validated_output, 'dict') else validated_output
                except Exception as e:
                    logger.warning(f"⚠️ [Registry] Output validation failed: {str(e)}, using raw result")
                    task.result = result
            else:
                task.result = result
            
            task.status = TaskStatus.COMPLETED
            logger.info(f"✅ [Registry] {task.worker.capitalize()} completed task: {task.id}")
            return True
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error(f"⚠️ [Registry] {task.worker.capitalize()} execution failed: {str(e)}")
            return False

