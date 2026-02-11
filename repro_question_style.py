
import os
import sys
import asyncio
import json
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.orchestrator import Orchestrator, ConversationState
from app.llm_factory import LLMFactory

# Load environment variables
load_dotenv()

async def test_question_generation():
    print("--- Verifying Question Generation Style ---")
    
    orchestrator = Orchestrator()
    state = ConversationState()
    state.investigation_phase = "PHASE1_FOUNDATIONAL"
    
    # Mock Checklist (similar to what was seen in the user's report)
    mock_checklist = [
        {
            "requirement": "근로기준법의 적용대상은 근로자이다",
            "type": "existence",
            "status": "UNKNOWN",
            "reason": ""
        },
        {
            "requirement": "상시 5인 이상의 근로자를 사용하는 사업장",
            "type": "existence",
            "status": "UNKNOWN",
            "reason": ""
        }
    ]
    
    # [Test Case 1] First UNKNOWN: worker status
    print("\n[Test Case 1] First UNKNOWN: worker status")
    question_response = orchestrator._generate_next_question(state, mock_checklist, "상황 파악 중")
    print(f"AI Response: {question_response}")
    
    verify_question(question_response)

    # [Test Case 2] Meta-sounding requirements (The ones that caused issues)
    print("\n[Test Case 2] Meta-sounding requirement")
    meta_checklist = [
        {
            "requirement": "근로계약 체결 및 구체적 근로조건 명시 여부",
            "type": "existence",
            "status": "UNKNOWN",
            "reason": ""
        }
    ]
    question_response = orchestrator._generate_next_question(state, meta_checklist, "상황 파악 중")
    print(f"AI Response: {question_response}")
    verify_question(question_response)

    # [Test Case 3] Phase 3 Transition style
    print("\n[Test Case 3] Phase 3 (Investigation) Style")
    state.investigation_phase = "PHASE3_INVESTIGATION"
    invest_checklist = [
        {
            "requirement": "임금 체불액 확인",
            "type": "detail",
            "status": "UNKNOWN",
            "reason": ""
        }
    ]
    question_response = orchestrator._generate_next_question(state, invest_checklist, "상황 파악 중")
    print(f"AI Response: {question_response}")
    verify_question(question_response)

def verify_question(question_response):
    # Check for meta-questions or knowledge questions
    forbidden_words = ["기준", "요건", "범위", "부합", "평가"]
    found_forbidden = [w for w in forbidden_words if w in question_response]
    
    if found_forbidden:
        print(f"  [ISSUE] Forbidden words found: {found_forbidden}")
    else:
        print("  [PASS] No forbidden meta-words found.")

    if "?" not in question_response:
        print("  [ISSUE] Response is not a question.")
    
    if "지휘" in question_response and "감독" in question_response:
        print("  [WARNING] Technical legal terminology (지휘/감독) used directly.")

if __name__ == "__main__":
    asyncio.run(test_question_generation())
