import json
from typing import Dict, Any, Optional

class JudgmentEngine:
    def __init__(self, steps_path: str):
        with open(steps_path, "r", encoding="utf-8") as f:
            self.steps = json.load(f)

    def get_step(self, step_id: str) -> Dict[str, Any]:
        return self.steps.get(step_id, self.steps.get("WAGE_WORKER_CHECK"))

    def get_next_step_id(self, current_step_id: str, fact_value: str) -> str:
        step = self.get_step(current_step_id)
        if "next" in step:
            return step["next"].get(fact_value, "END_INSUFFICIENT_INFO")
        return current_step_id

    def is_terminal(self, step_id: str) -> bool:
        return self.steps.get(step_id, {}).get("is_terminal", False)
