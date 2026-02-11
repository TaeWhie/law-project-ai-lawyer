import requests
import sys

def check_server():
    print("Checking server status at http://localhost:8000...")
    try:
        # Check health/root first
        try:
            r = requests.get("http://localhost:8000", timeout=2)
            print(f"Root endpoint status: {r.status_code}")
        except Exception as e:
            print(f"Root check failed: {e}")

        # Check chat endpoint with the payload that caused error
        print("Sending test chat message...")
        payload = {
            "message": "돈도 못받았는데 욕하며 그만두래",
            "client_id": "debugger_agent"
        }
        res = requests.post("http://localhost:8000/api/chat", json=payload, timeout=10)
        
        print(f"Chat API Status: {res.status_code}")
        if res.status_code != 200:
            print(f"Error Response: {res.text}")
        else:
            print("Success! Server returned 200.")
            print(res.json().get("response"))

    except Exception as e:
        print(f"Connection failed: {e}")
        print("The server appears to be down or unreachable.")

if __name__ == "__main__":
    check_server()
