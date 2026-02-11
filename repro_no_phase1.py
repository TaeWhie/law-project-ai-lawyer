
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.orchestrator import Orchestrator, ConversationState

# Load environment variables
load_dotenv()

async def test_no_phase1_flow():
    print("--- Verifying Conversation Flow WITHOUT Phase 1 ---")
    
    orchestrator = Orchestrator()
    state = ConversationState()

    # User Statement: "I wasn't paid for 3 months"
    user_input = "작년부터 3개월치 월급 천만원을 못 받았어요."
    print(f"\n[Step 1] User: '{user_input}'")
    
    # Process input
    response = orchestrator.process_input(user_input, state)
    
    print(f"\nAI Response: {response}")
    print(f"Current Phase: {state.investigation_phase}")
    
    # Check logic:
    # 1. Phase should be PHASE3_INVESTIGATION (or PHASE2_NARROWING if many articles)
    # 2. Checklist should NOT contain "Who is worker" etc. from Phase 1.
    # 3. Checklist should contain wage-related items.
    
    print("\n[State Analysis]")
    print(f"Detected Issues: {[i['korean'] for i in state.detected_issues]}")
    
    if state.issue_type in state.issue_checklist:
        checklist = state.issue_checklist[state.issue_type]
        print(f"Checklist for {state.issue_type}:")
        for item in checklist:
            print(f"- {item['requirement']} (Status: {item['status']})")
            
        # Verify absence of Phase 1 items
        foundational_keywords = ["근로자 신분", "사용자성", "상시 근로자"]
        found_foundational = [r['requirement'] for r in checklist if any(kw in r['requirement'] for kw in foundational_keywords)]
        
        if found_foundational:
            print(f"  [FAIL] Foundational items still present: {found_foundational}")
        else:
            print("  [PASS] No standalone foundational items in the checklist.")
            
        # Verify presence of wage items
        wage_keywords = ["임금", "지불", "금액", "지급"]
        found_wage = [r['requirement'] for r in checklist if any(kw in r['requirement'] for kw in wage_keywords)]
        if found_wage:
            print(f"  [PASS] Wage investigation items found: {found_wage[:2]}...")
        else:
            print("  [FAIL] No wage investigation items found.")

if __name__ == "__main__":
    asyncio.run(test_no_phase1_flow())
