from typing import Dict, List, Any
from facts.schemas import Fact, FactState

class ConversationState:
    def __init__(self, issue_type: str = ""):
        self.issue_type = issue_type # Legacy, will be updated to first detected key
        self.detected_issues: List[Dict[str, str]] = [] # [{"key": "...", "korean": "..."}]
        self.current_step = "START"
        self.facts: Dict[str, Fact] = {}
        self.judgment_ready = False
        self.message_log: List[Dict[str, str]] = []
        self.session_title: str = "새 상담"
        self.dynamic_issue_data: Dict[str, Any] = {} # For dynamic reasoning state
        self.issue_checklist: Dict[str, List[Dict[str, Any]]] = {} # {issue_key: [{"requirement": "...", "status": bool, "reason": "..."}]}
        self.issue_progress: Dict[str, int] = {} # {issue_key: int}
        self.verification_stage = "PENDING" # "PENDING", "REVIEW", "CONFIRMED"
        self.investigation_phase = "PHASE1_NARROWING" # PHASE1_NARROWING (Old Phase 2), PHASE2_INVESTIGATION (Old Phase 3)
        self.last_asked_item: str = "" # The 'requirement' string of the last question
        self.last_asked_item_text: str = "" # The literal text of the question
        self.cached_law_context: str = "" # RAG results cache
        self.cached_issue_key: str = "" # Key associated with the cache
        self.last_intent: str = "" # To avoid redundant classification
        # Category narrowing (Phase 0.5)
        self.narrowing_pending: bool = False  # Waiting for narrowing answer
        self.narrowing_options: List[Dict] = []  # LLM-generated options
        self.narrowing_issue_key: str = ""  # Issue being narrowed
        self.narrowing_filtered_articles: List[str] = []  # Filtered article keywords
        self.narrowing_depth: int = 0  # Current narrowing depth (for hierarchical narrowing)
        self.narrowing_current_articles: List[str] = []  # Current remaining article numbers
        self.selected_law: str = ""  # Auto-selected law based on user input (empty by default)

    def update_fact(self, fact_name: str, value: FactState, confidence: float = 1.0, source: str = "user"):
        from facts.schemas import FactSource
        self.facts[fact_name] = Fact(
            name=fact_name,
            value=value,
            confidence=confidence,
            source=FactSource(source)
        )

    def get_fact_value(self, fact_name: str) -> FactState:
        if fact_name in self.facts:
            return self.facts[fact_name].value
        return FactState.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "current_step": self.current_step,
            "issue_checklist": self.issue_checklist,
            "facts": {k: v.dict() for k, v in self.facts.items()},
            "judgment_ready": self.judgment_ready,
            "investigation_phase": self.investigation_phase
        }
