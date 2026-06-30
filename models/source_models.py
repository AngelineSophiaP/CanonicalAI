from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field 

class RawSourceData(BaseModel):
    source_name: str
    source_weight: int

class ParsedCSVRecord(RawSourceData):
    source_name: str = "recruiter_csv"
    source_weight: int = 100  # Highest priority for identity/contact
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    github_url: Optional[str] = None
    skills: Optional[str] = None

class ParsedResumeData(RawSourceData):
    source_name: str = "resume_pdf"
    source_weight: int = 80
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    extracted_skills: List[str] = Field(default_factory=list)

class ParsedGitHubData(RawSourceData):
    source_name: str = "github_api"
    source_weight: int = 90  # Highest priority for skills
    username: str
    profile_url: str
    bio: Optional[str] = None
    bio_skills: List[str] = Field(default_factory=list)
    repo_languages: List[str] = Field(default_factory=list)