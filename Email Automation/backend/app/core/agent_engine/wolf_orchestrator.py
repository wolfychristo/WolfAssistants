import logging
import time
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from .planner import Planner
from .registry import WorkerRegistry
from .critic import Critic
from .context import StateContext
from .models import Plan, Task, TaskStatus, AgentResponse, AuditResult

logger = logging.getLogger(__name__)

class WolfOrchestrator:
    """
    Core Orchestrator for WolfAssistants.
    Implements the Plan-Execute-Review loop with autonomous problem-solving.
    """
    
    def __init__(self, model: str = "gemini/gemini-pro"):
        self.planner = Planner(model=model)
        self.registry = WorkerRegistry()
        self.critic = Critic(model=model)
        self.context = StateContext()
        self.model = model

    def register_worker(
        self,
        name: str,
        worker_instance: Any,
        description: str = "",
        input_schema: Optional[Any] = None,
        output_schema: Optional[Any] = None,
        supported_actions: Optional[list] = None
    ):
        """Register a worker tool with the orchestrator."""
        self.registry.register(
            name=name,
            worker_instance=worker_instance,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            supported_actions=supported_actions
        )

    async def execute(
        self,
        goal: str,
        max_retries: int = 2,
        enable_review: bool = True
    ) -> AgentResponse:
        """
        Main execution method: Plan → Execute → Review
        
        Args:
            goal: User's goal/request
            max_retries: Maximum retry attempts for failed tasks
            enable_review: Whether to run the Review/Critic step
            
        Returns:
            AgentResponse with execution results
        """
        start_time = time.time()
        logger.info(f"\n🚀 [Orchestrator] Starting execution for goal: {goal}")
        
        # Initialize response
        response = AgentResponse(
            goal=goal,
            success=False,
            errors=[]
        )
        
        try:
            # ====================================================================
            # 1. PLAN: Decompose goal into tasks
            # ====================================================================
            logger.info("📋 [Orchestrator] Phase 1: Planning...")
            plan = self.planner.create_plan(goal)
            response.plan = plan
            logger.info(f"✅ [Orchestrator] Plan created with {len(plan.tasks)} tasks")
            
            # ====================================================================
            # 2. EXECUTE: Run tasks in order (respecting dependencies)
            # ====================================================================
            logger.info("⚙️ [Orchestrator] Phase 2: Executing tasks...")
            executed_tasks = set()
            
            for task in plan.tasks:
                # Check dependencies
                if task.dependencies:
                    unmet_deps = [dep for dep in task.dependencies if dep not in executed_tasks]
                    if unmet_deps:
                        logger.warning(f"⚠️ [Orchestrator] Task {task.id} has unmet dependencies: {unmet_deps}")
                        task.status = TaskStatus.SKIPPED
                        continue
                
                # Execute task with retries
                task.started_at = datetime.utcnow()
                success = False
                retry_count = 0
                
                while not success and retry_count <= max_retries:
                    if retry_count > 0:
                        task.status = TaskStatus.RETRYING
                        logger.info(f"🔄 [Orchestrator] Retrying task {task.id} (attempt {retry_count + 1})")
                    
                    success = await self.registry.execute_task(task, self.context)
                    
                    if not success:
                        retry_count += 1
                        if retry_count <= max_retries:
                            # Wait before retry (exponential backoff)
                            await asyncio.sleep(2 ** retry_count)
                
                task.completed_at = datetime.utcnow()
                
                if success:
                    executed_tasks.add(task.id)
                    logger.info(f"✅ [Orchestrator] Task {task.id} completed successfully")
                else:
                    response.errors.append(f"Task {task.id} failed after {max_retries + 1} attempts: {task.error}")
                    logger.error(f"❌ [Orchestrator] Task {task.id} failed: {task.error}")
                    # Continue with other tasks (non-blocking)
            
            # ====================================================================
            # 3. REVIEW: Audit results against original goal
            # ====================================================================
            if enable_review:
                logger.info("🔍 [Orchestrator] Phase 3: Reviewing results...")
                audit_result = await self.critic.audit(goal, plan, self.context)
                response.audit_result = audit_result
                
                if audit_result.is_valid:
                    logger.info("✅ [Orchestrator] Review passed")
                    response.success = True
                else:
                    logger.warning(f"⚠️ [Orchestrator] Review failed: {audit_result.feedback}")
                    response.errors.append(f"Review feedback: {audit_result.feedback}")
            else:
                # If review is disabled, consider it successful if no critical errors
                response.success = len(response.errors) == 0
            
            # Extract final result from context or last task
            if plan.tasks:
                last_task = plan.tasks[-1]
                if last_task.status == TaskStatus.COMPLETED:
                    response.final_result = last_task.result
                else:
                    # Try to get result from context
                    response.final_result = self.context.get("final_result")
            
            execution_time = time.time() - start_time
            response.execution_time_seconds = execution_time
            
            if response.success:
                logger.info(f"🏁 [Orchestrator] Goal accomplished in {execution_time:.2f}s")
            else:
                logger.warning(f"⚠️ [Orchestrator] Goal partially completed with errors")
            
            return response
            
        except Exception as e:
            error_msg = f"Orchestrator execution failed: {str(e)}"
            logger.error(f"💥 [Orchestrator] {error_msg}", exc_info=True)
            response.errors.append(error_msg)
            response.success = False
            response.execution_time_seconds = time.time() - start_time
            return response

    def get_registry_info(self) -> Dict[str, Any]:
        """Get information about registered workers."""
        return {
            "workers": [self.registry.get_worker_info(name) for name in self.registry.list_workers()],
            "total_workers": len(self.registry.list_workers())
        }

