from app.orchestrator import Orchestrator
from app.state import ConversationState
from facts.schemas import FactState
import os
from dotenv import load_dotenv

def test_sanjae_loop():
    load_dotenv()
    orchestrator = Orchestrator()
    state = ConversationState()
    
    # Simulate a state where safety_and_health is active
    state.issue_type = "safety_and_health"
    state.detected_issues = [{"key": "safety_and_health", "korean": "안전과 보건"}]
    state.current_step = "INVESTIGATING"
    
    # 1. First mention of treatment
    print("\n--- Turn 1: Treatment Mention ---")
    response1 = orchestrator.process_input("병원에서 치료를 받았어", state)
    print(f"AI response: {response1[:100]}...")
    
    # 2. Add the last question to log to simulate repetition check
    # (The server usually does this before the next process_input)
    
    # 3. Repeat the exact same answer or a very similar one
    print("\n--- Turn 2: Repeat/Specific Treatment ---")
    response2 = orchestrator.process_input("정신과 진료를 받았어", state)
    print(f"AI response: {response2[:100]}...")
    
    # Check if a loop was detected if the questions were identical
    # In a real scenario, if LLM repeats the question, Orchestrator should now catch it.
    
    # Check checklist
    checklist = state.issue_checklist.get("safety_and_health", [])
    treatment_item = next((i for i in checklist if "치료" in i["requirement"]), None)
    if treatment_item:
        print(f"Treatment Item Status: {treatment_item['status']}")
    
    # Check progress
    confirmed_count = sum(1 for item in checklist if item["status"] in ["YES", "NO", "INSUFFICIENT"])
    progress = int((confirmed_count / len(checklist)) * 100) if checklist else 0
    print(f"Progress: {progress}%")

if __name__ == "__main__":
    test_sanjae_loop()
