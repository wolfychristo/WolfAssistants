import json
import logging
from typing import List
from litellm import completion  # pyright: ignore[reportMissingImports]
from .models import Plan, Task, TaskStatus

logger = logging.getLogger(__name__)

class Planner:
    def __init__(self, model: str = "gemini/gemini-pro"):
        self.model = model

    def create_plan(self, goal: str) -> Plan:
        """Decompose a high-level goal into a sequence of JSON-validated tasks."""
        logger.info(f"🚧 [Planner] Generating plan for goal: {goal}")
        
        system_prompt = """
        You are the Head Architect of the WolfAssistants Agentic Engine. 
        Decompose the user's goal into a sequence of tasks for specialized workers:
        - wolfy: Scrapes and enriches lead data.
        - communicator: Drafts hyper-personalized outreach.
        - manager: Handles meetings and To-Do lists.

        Output MUST be a JSON object matching the Plan schema.
        Ensure tasks have correct dependencies and workers.
        """

        try:
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Goal: {goal}"}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            plan_dict = json.loads(content)
            
            # Validate with Pydantic
            plan = Plan(**plan_dict)
            logger.info(f"✅ [Planner] Plan created with {len(plan.tasks)} tasks.")
            return plan
            
        except Exception as e:
            logger.error(f"❌ [Planner] Failed to generate plan: {str(e)}")
            # Return a minimal failure plan or raise
            raise

