import requests
import time

# Wait for server to start
time.sleep(3)

url = "http://localhost:8000/calculate"
data = {
    "mass_tip": 100.0,
    "arm_len": 1000.0
}

try:
    response = requests.post(url, json=data)
    print(response.json())
except Exception as e:
    print(f"Error: {e}")
