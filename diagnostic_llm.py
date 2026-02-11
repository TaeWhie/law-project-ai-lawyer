import os
import openai
from dotenv import load_dotenv

load_dotenv()

def check_models():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        print("--- Listing Models ---")
        models = client.models.list()
        gpt_models = [m.id for m in models if "gpt" in m.id]
        print(f"Available GPT models: {gpt_models}")
        
        target = "gpt-5-nano"
        if target in [m.id for m in models]:
            print(f"\n[OK] {target} found!")
        else:
            print(f"\n[ERROR] {target} NOT found in model list.")
            
        print("\n--- Testing Single Call ---")
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Test known good first
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5
        )
        print(f"gpt-4o-mini response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    check_models()
