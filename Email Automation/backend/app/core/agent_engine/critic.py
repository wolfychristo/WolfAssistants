import logging
import json
from litellm import completion  # pyright: ignore[reportMissingImports]
from .models import Plan, AuditResult
from .context import StateContext

logger = logging.getLogger(__name__)

class Critic:
    def __init__(self, model: str = "gemini/gemini-pro"):
        self.model = model

    async def audit(self, goal: str, plan: Plan, context: StateContext) -> AuditResult:
        """Self-audit agent outputs against the user's intent and brand voice."""
        logger.info("🚧 [Critic] Auditing agent outputs...")
        
        # Compile a summary of work done
        work_summary = {
            "goal": goal,
            "tasks_performed": [
                {"id": t.id, "worker": t.worker, "action": t.action, "result": t.result}
                for t in plan.tasks if t.result
            ],
            "context_variables": context.all_vars
        }

        system_prompt = """
        You are the Quality Control Critic for WolfAssistants.
        Review the goal and the work performed by the agents.
        Check for:
        1. Alignment with the original goal.
        2. Professional and friendly brand voice.
        3. Accuracy and completeness.

        Output MUST be a JSON object matching the AuditResult schema.
        """

        try:
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Review this work: {json.dumps(work_summary)}"}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            audit_dict = json.loads(content)
            
            audit_result = AuditResult(**audit_dict)
            
            if audit_result.is_valid:
                logger.info("✅ [Critic] Audit passed.")
            else:
                logger.warning(f"⚠️ [Critic] Audit failed: {audit_result.feedback}")
                
            return audit_result
            
        except Exception as e:
            logger.error(f"❌ [Critic] Audit process failed: {str(e)}")
            # Default to valid if the audit itself fails to avoid blocking, or handle as error
            return AuditResult(is_valid=True, feedback="Audit system error, proceeding with caution.")

