import requests
import json

BASE_URL = "http://localhost:8000/api"
CLIENT_ID = "test_simultaneous_01"

def check():
    message = "돈을 못받았는데 욕하면서 해고래"
    print(f"Sent: {message}")
    
    response = requests.post(
        f"{BASE_URL}/chat", 
        json={"message": message, "client_id": CLIENT_ID}
    )
    
    if response.status_code == 200:
        data = response.json()
        issues = data.get("detected_issues", [])
        print("\n[Detected Issues]")
        for issue in issues:
            print(f"- {issue['korean']} ({issue['key']})")
            
        if len(issues) >= 3:
            print("\nSUCCESS: Detected 3 or more issues simultaneously.")
        else:
            print(f"\nResult: Detected {len(issues)} issues. (Expected 3)")
    else:
        print("Error:", response.text)

if __name__ == "__main__":
    check()
