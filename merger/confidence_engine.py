"""Confidence engine for assigning deterministic confidence values."""
from __future__ import annotations

from typing import Dict, List

from models.candidate import CandidateProfile, ProvenanceRecord


class ConfidenceEngine:
    """Calculate per-field and overall confidences for a candidate profile."""

    def __init__(self, base_confidences: Dict[str, float] | None = None) -> None:
        self.base_confidences = base_confidences or {"csv": 0.95, "resume": 0.80}

    def get_base_confidence(self, source: str) -> float:
        normalized = source.lower()
        return self.base_confidences.get(normalized, 0.80)

    def compute_skill_confidence(self, skill_name: str, sources: List[str], parse_results: List) -> float:
        """Compute skill-level confidence based on sources, frequency, and context.

        Rules implemented:
        - Base: if only 'resume' -> 0.65, else max base confidence among sources
        - If appears in 2+ distinct sources -> +0.1
        - If appears in job title/headline -> +0.1
        - Small boost for repeated mentions across parse_results
        - Clamp between 0 and 1
        """
        src_set = set(sources)
        if not src_set:
            base = 0.6
        elif src_set == {"resume"}:
            base = 0.65
        else:
            base = max(self.get_base_confidence(s) for s in src_set)

        boost = 0.0
        if len(src_set) >= 2:
            boost += 0.1

        # frequency: count occurrences in parse_results raw skills lists
        freq = 0
        for pr in parse_results:
            raw_skills = pr.raw.get("skills")
            if isinstance(raw_skills, list):
                for s in raw_skills:
                    if isinstance(s, str) and s.strip().lower() == skill_name.lower():
                        freq += 1
        if freq > 1:
            boost += min(0.05, 0.02 * (freq - 1))

        # title/headline check
        for pr in parse_results:
            # title in raw scalar fields
            title = pr.raw.get("title") or pr.raw.get("job_title") or pr.raw.get("headline")
            if isinstance(title, str) and skill_name.lower() in title.lower():
                boost += 0.1
                break

        conf = base + boost
        if conf > 1.0:
            conf = 1.0
        if conf < 0.0:
            conf = 0.0
        return round(conf, 3)

    def compute_overall_confidence(self, profile: CandidateProfile) -> float:
        """Compute overall confidence as mean of populated field confidences."""
        field_confidences: List[float] = []
        if profile.full_name:
            field_confidences.append(0.95 if any(p.field == "full_name" and p.source == "csv" for p in profile.provenance) else 0.80)
        if profile.emails:
            field_confidences.append(0.95 if any(p.field == "emails" and p.source == "csv" for p in profile.provenance) else 0.80)
        if profile.phones:
            field_confidences.append(0.95 if any(p.field == "phones" and p.source == "csv" for p in profile.provenance) else 0.80)
        if profile.skills:
            skill_confidence = max(skill.confidence for skill in profile.skills)
            field_confidences.append(skill_confidence)
        if profile.experience:
            experience_confidence = max(
                (self.base_confidences.get(p.source.lower(), 0.80) for p in profile.provenance if p.field == "experience"),
                default=0.80,
            )
            field_confidences.append(experience_confidence)
        if profile.education:
            education_confidence = max(
                (self.base_confidences.get(p.source.lower(), 0.80) for p in profile.provenance if p.field == "education"),
                default=0.80,
            )
            field_confidences.append(education_confidence)

        if not field_confidences:
            return 0.0
        return round(sum(field_confidences) / len(field_confidences), 3)
