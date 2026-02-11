import os
import time
from dotenv import load_dotenv

# Ensure we use GPT-5 for the orchestrator (High Quality Teacher)
# User Simulator uses gpt-5-nano (Low Cost Student) via explicit call in user_simulator.py
os.environ["OPENAI_MODEL_NAME"] = "gpt-5" 

from app.orchestrator import Orchestrator
from app.state import ConversationState
from data.user_simulator import UserSimulator

load_dotenv()

def synthesize_conversation(scenario: str, turns: int = 5):
    print(f"\n--- Starting Synthesis for Scenario: {scenario[:30]}... ---")
    
    # 1. Initialize System
    orchestrator = Orchestrator()
    state = ConversationState()
    
    # 2. Initialize User Simulator
    simulator = UserSimulator(scenario)
    
    # Initial trigger
    last_ai_msg = "안녕하세요! 어떤 법률 고민이 있으신가요?"
    print(f"AI: {last_ai_msg}")

    for i in range(turns):
        # User acts
        user_input = simulator.generate_response(last_ai_msg)
        print(f"User ({i+1}): {user_input}")
        
        # AI responds (DataCollector logs internally)
        last_ai_msg = orchestrator.process_input(user_input, state)
        print(f"AI ({i+1}): {last_ai_msg}")
        
        if "더 궁금한 점" in last_ai_msg or "상담을 종료" in last_ai_msg:
            break
            
        time.sleep(1) # Rate limit safety

if __name__ == "__main__":
    SCENARIOS = [
        "건설 현장에서 일하다가 사다리에서 떨어져 다리가 부러졌는데, 사장님이 치료비도 안 주고 해고하겠다고 협박함.",
        "식당 주방에서 끓는 물에 화상을 입었는데, 산재 처리는 커녕 내 부주의라며 월급에서 치료비를 깐다고 함.",
        "배달 일을 하다가 교통사고가 났는데, 오토바이 수리비를 물어내라고 하고 해고 통보를 받음."
    ]
    
    for scenario in SCENARIOS:
        synthesize_conversation(scenario, turns=7)
