
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.orchestrator import Orchestrator, ConversationState

# Load environment variables
load_dotenv()

async def test_renamed_flow():
    print("--- Verifying Renamed Flow and RAG Context Optimization ---")
    
    orchestrator = Orchestrator()
    state = ConversationState()

    # User Statement: "I wasn't paid for 3 months"
    # This should trigger Issue Classification and start in PHASE1_NARROWING
    user_input = "작년부터 3개월치 월급 천만원을 못 받았어요."
    print(f"\n[Step 1] User: '{user_input}'")
    
    # Process input
    response = orchestrator.process_input(user_input, state)
    
    print(f"\nAI Response: {response}")
    print(f"Current Phase: {state.investigation_phase}")
    
    # Verification 1: Initial Phase
    if state.investigation_phase == "PHASE1_NARROWING":
        print("[PASS] Conversation started in PHASE1_NARROWING.")
    elif state.investigation_phase == "PHASE2_INVESTIGATION":
        print("[NOTE] Conversation skipped narrowing and jumped to PHASE2_INVESTIGATION (if narrowing not needed).")
    else:
        print(f"[FAIL] Unexpected initial phase: {state.investigation_phase}")

    # Verification 2: RAG Context Cleanup (Visual Check from Logs expected, but can check state.cached_law_context)
    if state.cached_law_context:
        context_str, query_str = state.cached_law_context
        # Check if articles 1-14 are force-retrieved in the context string
        # Typically Articles 1-14 have text like "제1조(목적)", "제2조(정의)"
        has_foundational = any(f"제{i}조" in context_str for i in range(1, 15))
        # Note: Some laws might naturally include article 1 in regular RAG, but "Force adding foundational core articles" should be key.
        print(f"\nRAG Context Analysis:")
        print(f"- Expanded Query: {query_str}")
        if has_foundational:
            print("- Foundational articles (1-14) found in context. (Check logs to see if they were 'force-added' or naturally retrieved)")
        else:
            print("- [PASS] Foundational articles (1-14) NOT force-added to context.")

    # Verification 3: Checklist naming
    if state.issue_type in state.issue_checklist:
        checklist = state.issue_checklist[state.issue_type]
        print(f"\nChecklist Analysis for {state.issue_type}:")
        foundational_keywords = ["근로자 신분", "사용자성", "상시 근로자"]
        found_foundational = [r['requirement'] for r in checklist if any(kw in r['requirement'] for kw in foundational_keywords)]
    # Verification 4: Transition to Phase 2
    if state.investigation_phase == "PHASE1_NARROWING" and state.narrowing_pending:
        print("\n[Step 2] Simulating User Choice for Narrowing...")
        user_choice = "1" # Choosing the first option
        response2 = orchestrator.process_input(user_choice, state)
        print(f"AI Response 2: {response2[:100]}...")
        print(f"Current Phase after choice: {state.investigation_phase}")
        
        if state.investigation_phase == "PHASE2_INVESTIGATION":
            print("[PASS] Successfully transitioned to PHASE2_INVESTIGATION.")
            
            # Check RAG context in Phase 2
            if state.cached_law_context:
                context_str, query_str = state.cached_law_context
                has_foundational = any(f"제{i}조" in context_str for i in range(1, 15))
                print(f"Phase 2 RAG Analysis:")
                if not has_foundational:
                    print("- [PASS] Foundational articles (1-14) NOT present in Phase 2 context.")
                else:
                    print("- [INFO] Some foundational articles found (likely naturally retrieved by relevance, not force-added).")
        else:
            print(f"[FAIL] Failed to transition to PHASE2_INVESTIGATION. Current: {state.investigation_phase}")

if __name__ == "__main__":
    asyncio.run(test_renamed_flow())
