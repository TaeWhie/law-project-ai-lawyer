import os
import time
from llm.classifier import IssueClassifier
from dotenv import load_dotenv

load_dotenv()

def test_classifier():
    print("--- Testing Classifier with gpt-5-nano ---")
    user_input = "작년에 일하다가 부상을 당했는데 회사가 돈을 준다더니 한 푼도 안 줘."
    
    # Force use of gpt-5-nano
    classifier = IssueClassifier(model_name="gpt-5-nano")
    
    start_time = time.time()
    try:
        print("Classifying...")
        result = classifier.classify_issues(user_input)
        print(f"Result: {result}")
        print(f"Time taken: {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_classifier()
