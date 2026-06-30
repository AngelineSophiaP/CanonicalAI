import os
import requests
from dotenv import load_dotenv
load_dotenv(override=True)
from tenacity import retry, wait_exponential, stop_after_attempt
from models.source_models import ParsedGitHubData

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
def fetch_github_profile(username: str) -> ParsedGitHubData:
    # 1. GitHub REQUIRES a User-Agent header. 
    # Use your username or the app name.
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Eightfold-Candidate-Transformer"
    }
    
    # 2. Verify token is loading
    token = os.getenv("GITHUB_TOKEN")
    if token:
        # Some PATs are 'Bearer', some are 'token'
        headers["Authorization"] = f"token {token}"
    else:
        # If no token is found, this will likely hit the 60 req/hr limit instantly
        print("Warning: GITHUB_TOKEN not found in environment!")
        print(f"[DEBUG] Fetching GitHub with token starting: {token[:4]}")

    # 3. Fetch User
    user_url = f"https://api.github.com/users/{username}"
    user_resp = requests.get(user_url, headers=headers)
    
    # 4. Debugging: If it fails, print the status to see why
    if user_resp.status_code != 200:
        print(f"GitHub API Error {user_resp.status_code}: {user_resp.text}")
        user_resp.raise_for_status()
        
    user_data = user_resp.json()
    
    # 5. Fetch Repos
    repos_url = f"https://api.github.com/users/{username}/repos?per_page=50"
    repos_resp = requests.get(repos_url, headers=headers)
    repos_resp.raise_for_status()
    
    languages = set()
    for repo in repos_resp.json():
        if repo.get("language"):
            languages.add(str(repo["language"]).lower())
            
    bio = user_data.get("bio") or ""
    
    from src.utils.skill_engine import extract_canonical_skills
    bio_canonical = extract_canonical_skills(bio)
    
    return ParsedGitHubData(
        username=username,
        profile_url=user_data.get("html_url", ""),
        bio=bio,
        bio_skills=bio_canonical,
        repo_languages=list(languages)
    )