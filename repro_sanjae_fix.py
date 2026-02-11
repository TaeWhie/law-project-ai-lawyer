import os
import sys
from app.state import ConversationState
from app.orchestrator import Orchestrator

def test_sanjae_transition():
    orch = Orchestrator()
    state = ConversationState()
    
    print("\n=== STEP 1: Core Fact Investigation (CORE Phase) ===")
    user_input = "빵을 만들다 믹서기에 손가락이 잘렸어"
    print(f"User: {user_input}")
    response = orch.process_input(user_input, state)
    print(f"AI: {response[:200]}...")
    
    # Resolve CORE items (Status to YES)
    inputs = [
        "일하던 중에 사고가 났어",
        "오늘 아침 9시에 주방에서 일하다가 그랬어",
        "안전장비는 전혀 없었어"
    ]
    
    for inp in inputs:
        print(f"\nUser: {inp}")
        response = orch.process_input(inp, state)
        print(f"AI: {response[:200]}...")
        if "참고" in response:
            print(">>> [SUCCESS] Interim Summary reached.")
            break

    print("\n=== STEP 2: Transition to Deep Dive (PROCEED Intent) ===")
    user_input = "네 진행해주세요"
    print(f"User: {user_input}")
    response = orch.process_input(user_input, state)
    print(f"AI: {response[:200]}...")
    
    if state.investigation_phase == "DEEP" and state.verification_stage == "PENDING":
        print(">>> [SUCCESS] Transitioned to DEEP phase and RESET stage.")
    else:
        print(f">>> [FAILURE] Phase: {state.investigation_phase}, Stage: {state.verification_stage}")

    # Verify next question is DEEP
    print("\n=== STEP 3: Verify Deep Questioning (Evidence etc) ===")
    user_input = "네" # Continuation
    response = orch.process_input(user_input, state)
    print(f"AI: {response[:200]}...")

if __name__ == "__main__":
    test_sanjae_transition()
