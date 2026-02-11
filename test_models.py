import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

def test_connectivity():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not found in .env")
        return

    print(f"Using API Key (partial): {api_key[:10]}...")
    
    # Test gpt-4o-mini (Known Good)
    print("\n--- Testing gpt-4o-mini ---")
    try:
        llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
        response = llm.invoke("Say 'Mini OK'")
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"gpt-4o-mini Error: {e}")

    # Test gpt-5-nano (The New Model)
    print("\n--- Testing gpt-5-nano ---")
    try:
        # Set a short timeout to avoid indefinite hanging
        llm_nano = ChatOpenAI(model_name="gpt-5-nano", temperature=0, timeout=10)
        response_nano = llm_nano.invoke("Say 'Nano OK'")
        print(f"Response: {response_nano.content}")
    except Exception as e:
        print(f"gpt-5-nano Error: {e}")

if __name__ == "__main__":
    test_connectivity()
