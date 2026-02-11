import json
import os
from datetime import datetime
from typing import Dict, Any, List

class DataCollector:
    """
    Collects high-quality conversation data for fine-tuning.
    Logs successful interactions where the AI provided a structured JSON response.
    """
    def __init__(self, log_dir: str = "data/fine_tuning"):
        self.enabled = os.getenv("ENABLE_DATA_COLLECTION", "true").lower() == "true"
        if self.enabled:
            self.log_dir = log_dir
            os.makedirs(self.log_dir, exist_ok=True)
            self.log_file = os.path.join(self.log_dir, f"training_data_{datetime.now().strftime('%Y%m%d')}.jsonl")
        else:
            print("[DataCollector] Disabled by configuration.")

    def log_interaction(self, user_input: str, ai_response: str, metadata: Dict[str, Any] = None):
        if not self.enabled:
            return
        """
        Logs a single turn of conversation.
        Only logs if the AI response is valid JSON (implicit quality check).
        """
        try:
            # Validate JSON structure (essential for fine-tuning target)
            if ai_response.strip().startswith("{") or ai_response.strip().startswith("["):
                json.loads(ai_response) # Check if valid JSON
            else:
                # If not JSON, it might be chitchat or error, skip logging for now
                # Or log as 'text' type if we want to train chitchat model
                if metadata and metadata.get("intent") == "CHITCHAT":
                    pass # Optional: log chitchat
                else:
                    return # Skip invalid/non-JSON responses for core logic training

            entry = {
                "timestamp": datetime.now().isoformat(),
                "input": user_input,
                "output": ai_response,
                "metadata": metadata or {}
            }

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                
            print(f"[DataCollector] Logged interaction to {self.log_file}")

        except json.JSONDecodeError:
            print(f"[DataCollector] Skipped logging: AI response is not valid JSON.")
        except Exception as e:
            print(f"[DataCollector] Error logging interaction: {e}")

# Example Usage:
# collector = DataCollector()
# collector.log_interaction("해고당했어", '{"intent": "INVESTIGATION", ...}')
