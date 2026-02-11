import os
import time
from app.orchestrator import Orchestrator
from app.state import ConversationState

def verify_hybrid():
    print("--- Verifying Hybrid Model Latency ---")
    orch = Orchestrator()
    state = ConversationState()
    
    # 1. Test Chitchat (Should be fast)
    print("\n[Test 1] Chitchat (Fast Model)...")
    start = time.time()
    orch.process_input("안녕", state)
    print(f"Latency: {time.time() - start:.2f}s")
    
    # 2. Test Investigation (Should have ONE slow call)
    print("\n[Test 2] Investigation (GPT-5 Brain + Fast Utilities)...")
    start = time.time()
    orch.process_input("믹서기에 손가락이 다쳤어", state)
    print(f"Latency: {time.time() - start:.2f}s")

if __name__ == "__main__":
    verify_hybrid()
