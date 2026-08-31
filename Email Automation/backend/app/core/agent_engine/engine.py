import logging
from typing import Optional
from .planner import Planner
from .registry import WorkerRegistry
from .critic import Critic
from .context import StateContext
from .models import TaskStatus, Plan

from .workers.wolfy import WolfyWorker
from .workers.communicator import CommunicatorWorker
from .workers.manager import ManagerWorker

logger = logging.getLogger(__name__)

class AgenticEngine:
    def __init__(self, model: str = "gemini/gemini-pro"):
        self.planner = Planner(model=model)
        self.registry = WorkerRegistry()
        self.critic = Critic(model=model)
        self.context = StateContext()
        
        # Auto-register default workers with metadata
        wolfy = WolfyWorker()
        self.registry.register(
            name="wolfy",
            worker_instance=wolfy,
            description=wolfy.description,
            supported_actions=wolfy.supported_actions
        )
        
        communicator = CommunicatorWorker()
        self.registry.register(
            name="communicator",
            worker_instance=communicator,
            description=communicator.description,
            supported_actions=communicator.supported_actions
        )
        
        manager = ManagerWorker()
        self.registry.register(
            name="manager",
            worker_instance=manager,
            description=manager.description,
            supported_actions=manager.supported_actions
        )

    async def run_goal(self, goal: str) -> bool:
        """
        The main Plan-Execute-Review loop.
        """
        print(f"\n🚀 Starting WolfAssistants Agentic Engine...")
        print(f"🎯 Goal: {goal}")
        
        try:
            # 1. PLAN
            plan = self.planner.create_plan(goal)
            
            # 2. EXECUTE
            for task in plan.tasks:
                success = await self.registry.execute_task(task, self.context)
                
                # Autonomous Problem-Solving: Self-Correction Loop
                if not success:
                    print(f"⚠️ Task {task.id} failed. Attempting autonomous self-correction...")
                    # In a full implementation, we would re-plan here
                    # For now, we attempt a single re-run or log failure
                    success = await self.registry.execute_task(task, self.context)
                    if not success:
                        print(f"❌ Self-correction failed for task {task.id}. Escalating.")
                        return False

            # 3. REVIEW
            audit_result = await self.critic.audit(goal, plan, self.context)
            
            if audit_result.is_valid:
                print(f"🏁 ✅ Goal Accomplished Successfully: {goal}\n")
                return True
            else:
                print(f"⚠️ Audit feedback: {audit_result.feedback}")
                print(f"🚧 Suggested changes: {audit_result.suggested_changes}")
                return False

        except Exception as e:
            logger.error(f"💥 Engine failed to execute goal: {str(e)}")
            print(f"💥 Engine error: {str(e)}")
            return False

