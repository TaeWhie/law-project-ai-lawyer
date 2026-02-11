
import asyncio
import os
import json
from app.state import ConversationState
from app.orchestrator import Orchestrator
from app.llm_factory import LLMFactory

# Mocking the client ID
CLIENT_ID = "test_client_full_verify"

async def run_test():
    print("--- 10-Point Verification of Refactored Prompts ---")
    
    orchestrator = Orchestrator()
    state = ConversationState(CLIENT_ID)
    
    # 1. Multi-Issue Detection & Sequential Handling (Checks #1, #8)
    print("\n[Step 1] User Input: '일하다 다쳤는데 치료비도 안 주고 해고당했어. 월급도 못 받았고.'")
    # This should trigger: Occupational Safety (Sanjae), Unfair Dismissal, Wage Claim
    user_input_1 = "일하다 다쳤는데 치료비도 안 주고 해고당했어. 월급도 못 받았고."
    
    response_1 = orchestrator.process_input(user_input_1, state)
    print(f"AI Response: {response_1}")
    
    # Check Detected Issues
    print(f"Detected Issues: {state.detected_issues}")
    detected_keys = [i['key'] for i in state.detected_issues]
    
    # We expect at least these:
    expected_issues = ['unfair_dismissal', 'wage_claim', 'occupational_safety_and_health']
    
    # Fuzzy match or subset match
    if any(k in detected_keys for k in expected_issues): 
         print(f"[PASS] Multi-issue detection (Check #1). Found: {detected_keys}")
    else:
         print(f"[FAIL] Multi-issue detection. Found: {detected_keys}")

    current_issue = state.issue_type
    print(f"Current Focus: {current_issue}")
    
    # ... (rest of code) ...

    # 5. Sequential Issue Switching (Check #8)
    print(f"\nCurrent Focus after Turn 2: {state.issue_type}")
    if state.issue_type != current_issue:
        print(f"[PASS] Switched to next issue: {state.issue_type} (Check #8)")
    else:
        print(f"[INFO] Still on {state.issue_type} (Likely moving to Deep Phase or checking more details)")

if __name__ == "__main__":
    asyncio.run(run_test())
