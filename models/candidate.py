"""Pydantic models for the canonical CandidateProfile and related types.

This module contains the core data models used across the pipeline.
"""
from __future__ import annotations

import sys
# Prevent duplicate namespace issues when candidate_transformer is imported relatively vs absolutely
if "candidate_transformer.models.candidate" in sys.modules and "models.candidate" not in sys.modules:
    sys.modules["models.candidate"] = sys.modules["candidate_transformer.models.candidate"]
elif "models.candidate" in sys.modules and "candidate_transformer.models.candidate" not in sys.modules:
    sys.modules["candidate_transformer.models.candidate"] = sys.modules["models.candidate"]

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, root_validator, validator


class ProvenanceRecord(BaseModel):
    field: str
    source: str
    method: str
    value: Optional[Any] = None
    index: Optional[int] = None


class Skill(BaseModel):
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)

    @validator("name")
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("skill name must not be empty")
        return v.strip()


class ExperienceEntry(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None  # ISO YYYY-MM or None
    end: Optional[str] = None
    summary: Optional[str] = None


class EducationEntry(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[int] = None


class ParseResult(BaseModel):
    source: str
    raw: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CandidateProfile(BaseModel):
    candidate_id: str
    full_name: Optional[str] = None
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    location: Dict[str, Optional[str]] = Field(
        default_factory=lambda: {"city": None, "region": None, "country": None}
    )
    links: Dict[str, Any] = Field(
        default_factory=lambda: {
            "linkedin": None,
            "github": None,
            "portfolio": None,
            "other": [],
        }
    )
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: List[Skill] = Field(default_factory=list)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    provenance: List[ProvenanceRecord] = Field(default_factory=list)
    overall_confidence: float = Field(0.0, ge=0.0, le=1.0)

    @validator("emails", each_item=True)
    def strip_emails(cls, v: str) -> str:
        return v.strip()

    @validator("phones", each_item=True)
    def strip_phones(cls, v: str) -> str:
        return v.strip()

    @root_validator(skip_on_failure=True)
    def normalize_overall_confidence(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        oc = values.get("overall_confidence")
        if oc is None:
            values["overall_confidence"] = 0.0
        # ensure in-bounds; pydantic Field already enforces but normalize defensively
        if values["overall_confidence"] < 0.0:
            values["overall_confidence"] = 0.0
        if values["overall_confidence"] > 1.0:
            values["overall_confidence"] = 1.0
        return values
