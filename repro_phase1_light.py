
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

async def test_phase1_light():
    print("--- Verifying Phase 1 Light Logic (Verbal Confirmation Only) ---")
    
    # Initialize Orchestrator
    orchestrator = Orchestrator()
    state = ConversationState()

    # 1. User Statement: "I wasn't paid"
    print("\n[Step 1] User: '작년에 일하다가 부상을 당했는데 회사가 돈을 준다더니 한 푼도 안 줘.'")
    response = orchestrator.process_input("작년에 일하다가 부상을 당했는데 회사가 돈을 준다더니 한 푼도 안 줘.", state)
    print(f"AI Response: {response}")

    # Check logic: Should identify wage claim and ask for basic facts (amount/period) OR confirm existence.
    # It should NOT ask for documents.
    
    # 2. User Statement: "3 months, 10 million won"
    print("\n[Step 2] User: '세 달 동안 일을 못했으니까 약 천 만원이야'")
    response = orchestrator.process_input("세 달 동안 일을 못했으니까 약 천 만원이야", state)
    print(f"AI Response: {response}")

    # Check logic: 
    # - Should mark 'Existence' (Level 1) as YES because user confirmed amount/period verbally.
    # - Should NOT ask "Do you have a contract?".
    # - Should likely move to DONE (Phase 1 complete) or ask a final confirmation.
    
    print("\n[State Analysis]")
    if state.detected_issues:
        issue = state.detected_issues[0]
        print(f"Issue: {issue['korean']}")
        
        if issue['key'] in state.issue_checklist:
            checklist = state.issue_checklist[issue['key']]
            print(f"Checklist Items: {len(checklist)}")
            for item in checklist:
                print(f"- {item['requirement']}: {item['status']} ({item.get('reason', '')})")
                
                # Validation: Evidence requests in Phase 1 are FAIL
                if "증거" in item['requirement'] or "자료" in item['requirement'] or "계약서" in item['requirement']:
                    print("  [FAIL] Evidence requirement found in Phase 1 Checklist!")
                
    else:
        print("No issues detected.")

if __name__ == "__main__":
    asyncio.run(test_phase1_light())
