import os
import sys
from app.state import ConversationState
from app.orchestrator import Orchestrator

def test_two_phase_workflow():
    orch = Orchestrator()
    state = ConversationState()
    
    print("\n=== STEP 1: Core Fact Investigation (CORE Phase) ===")
    # Initial input: multiple issues
    user_input = "돈도 못받았는데 욕하며 그만두래"
    print(f"User: {user_input}")
    response = orch.process_input(user_input, state)
    print(f"AI: {response[:200]}...")
    print(f"Current Phase: {state.investigation_phase}")
    print(f"Current Issue: {state.issue_type}")
    
    # Help AI resolve CORE facts
    inputs = [
        "600만원 3개월",
        "해고를 당하진 않았어", # Resolve dismissal as NO
        "아침마다 병신이라 욕하며 이렇게 할꺼면 나가라고 막말을 했어" # Resolve harassment as CORE YES
    ]
    
    for inp in inputs:
        print(f"\nUser: {inp}")
        response = orch.process_input(inp, state)
        print(f"AI: {response[:200]}...")
        print(f"Phase: {state.investigation_phase}, Issue: {state.issue_type}")
        if "참고: 더 구체적인 고소 준비" in response:
            print(">>> [SUCCESS] Interim Summary detected at the end of CORE phase.")
            break

    print("\n=== STEP 2: Transition to Deep Dive (PROCEED Intent) ===")
    user_input = "네 진행해주세요"
    print(f"User: {user_input}")
    response = orch.process_input(user_input, state)
    print(f"AI: {response[:200]}...")
    print(f"Current Phase: {state.investigation_phase}")
    print(f"Current Issue: {state.issue_type}")
    
    if state.investigation_phase == "DEEP":
        print(">>> [SUCCESS] Transitioned to DEEP phase.")
    else:
        print(">>> [FAILURE] Failed to transition to DEEP phase.")

if __name__ == "__main__":
    test_two_phase_workflow()
