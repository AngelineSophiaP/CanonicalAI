import re
from typing import List, Optional, Dict, Set
from pydantic import BaseModel, EmailStr, Field, field_validator
import phonenumbers

class ContactInfo(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    github_url: Optional[str] = None

    @field_validator('phone')
    @classmethod
    def normalize_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        try:
            # Assumes IN/US context if country code is missing, defaults to E164
            parsed = phonenumbers.parse(v, "IN")
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            cleaned = re.sub(r'[^\d+]', '', v)
            return cleaned if cleaned else None

class CanonicalCandidate(BaseModel):
    candidate_id: str = Field(..., description="Unique identifier (e.g., email or github username)")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    contact: ContactInfo = Field(default_factory=ContactInfo)
    skills: List[str] = Field(default_factory=list)
    
    # Internal metadata tracking field -> source
    provenance_metadata: Dict[str, str] = Field(default_factory=dict, exclude=True)
    
    # Internal metadata tracking field -> weight
    _weights: Dict[str, int] = {}

    @field_validator('skills')
    @classmethod
    def normalize_skills(cls, v: List[str]) -> List[str]:
        cleaned_skills = {skill.strip().lower() for skill in v if skill.strip()}
        return sorted(list(cleaned_skills))