
import asyncio
from app.state import ConversationState
from app.orchestrator import Orchestrator

# Mocking the client ID
CLIENT_ID = "test_client_multi_issue_mid"

async def run_test():
    print("--- Testing Multi-Issue Detection Mid-Conversation ---")
    
    orchestrator = Orchestrator()
    state = ConversationState(CLIENT_ID)
    
    # Turn 1: Wage Claim only
    print("\n[Turn 1] User: '사장님이 월급을 안 줘.'")
    res1 = orchestrator.process_input("사장님이 월급을 안 줘.", state)
    print(f"Detected Issues (Turn 1): {[i['key'] for i in state.detected_issues]}")
    
    if "wage_claim" in [i['key'] for i in state.detected_issues] and len(state.detected_issues) == 1:
        print("[PASS] Turn 1 correctly detected only Wage Claim.")
    else:
        print(f"[FAIL] Turn 1 detection mismatch. Got: {state.detected_issues}")

    # Turn 2: Mention Harassment
    # This should trigger the new logic in Orchestrator to append 'workplace_harassment'
    print("\n[Turn 2] User: '그리고 부장님이 욕도 하고 때렸어.'")
    res2 = orchestrator.process_input("그리고 부장님이 욕도 하고 때렸어.", state)
    
    detected_keys_2 = [i['key'] for i in state.detected_issues]
    print(f"Detected Issues (Turn 2): {detected_keys_2}")
    
    if "workplace_harassment" in detected_keys_2:
        print("[PASS] Turn 2 successfully added Workplace Harassment.")
    else:
        print("[FAIL] Turn 2 failed to add Workplace Harassment.")
        
    # Turn 3: Check if both are in state
    if "wage_claim" in detected_keys_2 and "workplace_harassment" in detected_keys_2:
        print("[PASS] Both issues are preserved in state.")
    else:
        print("[FAIL] State lost previous issue.")

if __name__ == "__main__":
    asyncio.run(run_test())
