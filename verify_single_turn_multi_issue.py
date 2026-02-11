
import asyncio
from app.state import ConversationState
from app.orchestrator import Orchestrator

# Mocking the client ID
CLIENT_ID = "test_client_single_turn_multi"

async def run_test():
    print("--- Testing Single-Turn Multi-Issue Detection ---")
    
    orchestrator = Orchestrator()
    state = ConversationState(CLIENT_ID)
    
    # User's exact example
    user_input = "사장님이 돈도 안주고 욕하며 날 때려"
    print(f"\nUser Input: '{user_input}'")
    
    res = orchestrator.process_input(user_input, state)
    
    print(f"\n[Detected Issues]")
    for issue in state.detected_issues:
        print(f"- Key: {issue['key']}, Korean: {issue['korean']}")
        
    keys = [i['key'] for i in state.detected_issues]
    
    # Expected: wage_claim AND (workplace_harassment OR assault)
    # Note: 'assault' might be under harassment or separate depending on categories.
    # checking based on standard set.
    
    if "wage_claim" in keys and "workplace_harassment" in keys:
        print("\n[SUCCESS] Detected both Wage Claim and Harassment.")
    else:
        print(f"\n[FAIL] Detection incomplete. Found: {keys}")

if __name__ == "__main__":
    asyncio.run(run_test())
