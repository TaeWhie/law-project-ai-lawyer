import requests
import json

def probe():
    url = "http://localhost:8000/api/chat"
    # Match script.js behavior: sessionId is null initially
    payload = {
        "message": "돈도 못받았는데 욕하며 그만두래",
        "client_id": "test_client_id",
        "session_id": None
    }
    
    print(f"Sending payload: {json.dumps(payload, ensure_ascii=False)}")
    r = requests.post(url, json=payload)
    print(f"Status Code: {r.status_code}")
    print(f"Response Body: {r.text}")

if __name__ == "__main__":
    probe()
