import os
import requests
from dotenv import load_dotenv

# Force load the .env
load_dotenv(override=True)
token = os.getenv("GITHUB_TOKEN")
print(f"Token loaded: {bool(token)}")
headers = {"Authorization": f"token {token}", "User-Agent": "test"}
resp = requests.get("https://api.github.com/user", headers=headers)
print(f"Status Code: {resp.status_code}")
print(f"Response: {resp.json().get('login') if resp.status_code == 200 else resp.text}")