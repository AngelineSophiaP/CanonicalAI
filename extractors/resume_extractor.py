import re
import pdfplumber
import spacy
from datetime import datetime
from thefuzz import process, fuzz
from models.source_models import ParsedResumeData
from src.utils.text_cleaners import extract_email, extract_phone
from src.utils.skill_engine import extract_canonical_skills

# Load the local ML Model (Ensure you've run: python -m spacy download en_core_web_sm)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise RuntimeError("ML model not found. Run: python -m spacy download en_core_web_sm")

def extract_links(text: str) -> dict:
    """Extracts links using strict URL patterns."""
    urls = re.findall(r'(https?://[^\s]+)', text)
    links = {}
    for url in urls:
        clean_url = url.rstrip('/\\')
        if "github.com" in clean_url.lower(): links["github"] = clean_url
        elif "linkedin.com" in clean_url.lower(): links["linkedin"] = clean_url
        elif "leetcode.com" in clean_url.lower(): links["leetcode"] = clean_url
        else: links["portfolio"] = clean_url
    return links

def extract_name_ml(text: str) -> tuple[str | None, str | None]:
    """Uses spaCy NER to identify the Person entity."""
    doc = nlp(text[:1000])  # Header-focused processing
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            parts = re.sub(r'[^a-zA-Z\s]', '', ent.text).split()
            if 2 <= len(parts) <= 4:
                return parts[0].title(), " ".join(parts[1:]).title()
    return None, None

def extract_experience_ml(text: str) -> float | None:
    """Uses spaCy Date entities to estimate total experience."""
    doc = nlp(text)
    years = {int(y) for y in re.findall(r'\b(20\d{2})\b', text) if int(y) > 2000}
    if years:
        total_exp = datetime.now().year - min(years)
        return float(max(0, total_exp))
    return None

def parse_pdf_resume(file_path: str) -> ParsedResumeData:
    """Main Orchestrator."""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            content = page.extract_text()
            if content: text += content + "\n"
    
    first, last = extract_name_ml(text)
    
    canonical = extract_canonical_skills(text)
    
    return ParsedResumeData(
        first_name=first,
        last_name=last,
        email=extract_email(text),
        phone=extract_phone(text),
        links=extract_links(text),
        experience_years=extract_experience_ml(text),
        extracted_skills=canonical
    )