"""Tests for merge and confidence engines."""
from __future__ import annotations

from candidate_transformer.models.candidate import ParseResult
from candidate_transformer.merger.merge_engine import MergeEngine


def test_merge_prefers_csv_for_conflicting_name_and_normalizes_values():
    csv_result = ParseResult(
        source="csv",
        raw={
            "name": "Alice Smith",
            "email": "alice@example.com",
            "phone": "(415) 555-2671",
            "current_company": "Acme",
            "title": "Engineer",
        },
    )
    resume_result = ParseResult(
        source="resume",
        raw={
            "full_name": "Alice Johnson",
            "skills": ["python programming", "js"],
            "experience": [{"company": "Beta", "title": "Developer", "summary": "Built tools"}],
            "education": [{"institution": "MIT", "degree": "BS", "field": "CS", "end_year": 2020}],
        },
    )

    profile = MergeEngine().merge([csv_result, resume_result], candidate_id="cand-1")

    assert profile.full_name == "Alice Smith"
    assert profile.emails == ["alice@example.com"]
    assert profile.phones == ["+14155552671"]
    assert [skill.name for skill in profile.skills] == ["Python", "JavaScript"]
    assert profile.overall_confidence > 0.0
    assert any(p.field == "full_name" and p.source == "csv" for p in profile.provenance)
    assert any(p.field == "skills" and p.source == "resume" for p in profile.provenance)
