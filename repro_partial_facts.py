
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.orchestrator import Orchestrator, ConversationState
from app.llm_factory import LLMFactory

# Load environment variables
load_dotenv()

async def test_partial_facts():
    print("--- Verifying Partial Fact Acceptance & Checklist Dedupe ---")
    
    # Initialize Orchestrator
    orchestrator = Orchestrator()
    state = ConversationState()

    # 1. User Statement: "Finger cut off by bread machine" (Details provided, but maybe Time missing)
    print("\n[Step 1] User: '빵 만드는 기계에 손가락이 잘렸어'")
    # We simulate a state where current issue is safety_and_health
    state.detected_issues = [{"key": "safety_and_health", "korean": "안전과 보건"}]
    state.issue_type = "safety_and_health"
    
    response = orchestrator.process_input("빵 만드는 기계에 손가락이 잘렸어", state)
    print(f"AI Response: {response}")

    # Check logic:
    # - Should NOT ask "Tell me how it happened" (because user just said it).
    # - Should ask "When did it happen?" (Missing info).
    
    # 2. User Statement: "Last week" (Time provided)
    print("\n[Step 2] User: '저번 주야'")
    response2 = orchestrator.process_input("저번 주야", state)
    print(f"AI Response: {response2}")
    
    # Check logic:
    # - Should mark existence/details as YES.
    # - should NOT loop back to "Tell me details".

    print("\n[Checklist Analysis]")
    if "safety_and_health" in state.issue_checklist:
        checklist = state.issue_checklist["safety_and_health"]
        print(f"Total Items: {len(checklist)}")
        reqs = [item['requirement'] for item in checklist]
        for req in reqs:
            print(f"- {req}")
        
        # Dedupe check
        unique_reqs = set(reqs)
        if len(reqs) != len(unique_reqs):
             print(f"  [WARN] Potential duplicates found! ({len(reqs)} items, {len(unique_reqs)} unique strings)")
        else:
             print("  [PASS] No exact duplicates found.")

if __name__ == "__main__":
    asyncio.run(test_partial_facts())
