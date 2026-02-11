import os
import sys
import warnings
from app.state import ConversationState
from app.orchestrator import Orchestrator
from dotenv import load_dotenv

# Suppress warnings for cleaner UI
warnings.filterwarnings("ignore", category=DeprecationWarning)
load_dotenv()

# Ensure we are in the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("=== 대한민국 근로기준법 상담 챗봇 (임금체불 MVP) ===")
    
    llm_type = os.getenv("LLM_TYPE", "openai").upper()
    embed_type = os.getenv("EMBEDDING_TYPE", os.getenv("LLM_TYPE", "openai")).upper()
    print(f"[System] LLM: {llm_type} | Embed: {embed_type}")
    
    print("상담을 시작합니다. 상황을 설명해 주세요.")
    
    orchestrator = Orchestrator()
    state = ConversationState()
    
    while not state.judgment_ready:
        user_input = input("\n[사용자]: ")
        if user_input.lower() in ["quit", "exit", "종료"]:
            break
            
        response = orchestrator.process_input(user_input, state)
        print(f"\n[AI]: {response}")
        
    print("\n상담이 종료되었습니다. 이용해 주셔서 감사합니다.")
    input("\n종료하려면 Enter 키를 누르세요...")

if __name__ == "__main__":
    # Check for API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("경고: OPENAI_API_KEY 환경 변수가 설정되어 있지 않습니다.")
    
    main()
