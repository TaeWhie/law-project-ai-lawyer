
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.orchestrator import Orchestrator, ConversationState

# Load environment variables
load_dotenv()

async def test_taxonomical_narrowing():
    print("--- Verifying Taxonomical Narrowing Flow ---")
    print("Test Case: '돈을 못받았어' (Broad wage-related query)")
    
    orchestrator = Orchestrator()
    state = ConversationState()

    # User Statement: Broad query
    user_input = "돈을 못받았어"
    print(f"\n[Step 1] User: '{user_input}'")
    
    # Process input
    response = orchestrator.process_input(user_input, state)
    
    print(f"\nAI Response:\n{response}")
    print(f"\nCurrent Phase: {state.investigation_phase}")
    
    # Analysis
    if state.narrowing_options:
        print("\n[Narrowing Options Analysis]")
        for i, opt in enumerate(state.narrowing_options):
            print(f"{i+1}. {opt['label']} (Articles: {opt['article_numbers']})")
        
        # Check if the labels look like legal taxonomy (taxonomical grouping)
        taxonomical_keywords = ["구성", "지급", "시기", "정산", "수당", "보상", "원칙"]
        score = sum(1 for opt in state.narrowing_options if any(kw in opt['label'] for kw in taxonomical_keywords))
        
        if score >= 2:
            print(f"\n[PASS] Taxonomical keywords found in {score} options.")
        else:
            print(f"\n[NOTE] Taxonomical keywords found in {score} options. Review manual output.")
    else:
        print("\n[FAIL] No narrowing options generated.")

    # Verification of transition with number
    if state.narrowing_pending:
        print("\n[Step 2] Simulating numeric choice '1'...")
        response2 = orchestrator.process_input("1", state)
        print(f"\nAI Response 2 (Investigation Start):\n{response2[:200]}...")
        if state.investigation_phase == "PHASE2_INVESTIGATION":
            print("[PASS] Successfully transitioned to Phase 2 with numeric input.")
        else:
            print(f"[FAIL] Transition failed. Phase: {state.investigation_phase}")

if __name__ == "__main__":
    asyncio.run(test_taxonomical_narrowing())
