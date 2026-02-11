
import asyncio
import os
from app.state import ConversationState
from app.orchestrator import Orchestrator

# Mocking the client ID
CLIENT_ID = "test_client_time_flexibility"

async def run_test():
    print("--- Verifying Time Flexibility (Relative Dates) ---")
    
    # 1. Initialize Orchestrator
    orchestrator = Orchestrator()
    
    # 2. Initialize State
    state = ConversationState(CLIENT_ID) 
    
    # 3. Simulate User Input: Initial vague statement
    user_input_1 = "작년에 다쳐서 치료받았어"
    print(f"\n[Step 1] User: '{user_input_1}'")
    
    response_1 = await orchestrator.process_input(user_input_1, state)
    print(f"AI Response: {response_1}")
    
    # Check if 'safety_and_health' issue is detected and Level 1 is likely YES (due to specific injury description if added, or just existence)
    # Actually, "treated" implies existence.
    
    # 4. Simulate User Input: Specific Relative Time
    # AI might ask "When specifically?" if it didn't catch "Last year" in the first turn.
    # But if it did, it should be done. 
    # Let's assume the AI *missed* the time in step 1 or asked for clarification.
    # The log showed the AI asking "When exactly?" after the user said "Last year".
    # So let's reproduce that flow.
    
    # Reset state for a cleaner repro of the specific failure case from logs
    state = ConversationState(CLIENT_ID)
    
    # Turn 1: Context setting
    await orchestrator.process_input("일하다가 다쳤어", state)
    
    # Turn 2: AI asks when/where. User says "Last year"
    user_input_2 = "작년에 그랬어" 
    print(f"\n[Step 2] User: '{user_input_2}'")
    
    response_2 = await orchestrator.process_input(user_input_2, state)
    print(f"AI Response: {response_2}")
    
    # Check if the AI accepts it or asks again.
    # Access internal state to verify checklist status for "Date/Time"
    checklist = state.issue_checklist.get('safety_and_health', [])
    print("\n[Checklist Status]")
    for item in checklist:
        print(f"- {item['requirement']}: {item['status']}")
        
    # We expect the relevant requirement (Time/Date) to be YES, not NO/UNKNOWN.

if __name__ == "__main__":
    asyncio.run(run_test())
