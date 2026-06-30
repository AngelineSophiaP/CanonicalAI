import re

def extract_email(text: str) -> str | None:
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return match.group(0) if match else None

def extract_phone(text: str) -> str | None:
    match = re.search(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}', text)
    return match.group(0) if match else None

def extract_github_username(input_str: str) -> str:
    """Extracts the username from a raw GitHub URL or handle."""
    # If it's already just a username, return it
    if "/" not in input_str and "@" not in input_str:
        return input_str
        
    # Regex to extract the handle after github.com/
    match = re.search(r'github\.com/([a-zA-Z0-9-]+)', input_str)
    if match:
        return match.group(1)
        
    # Handle @user format
    return input_str.lstrip('@')