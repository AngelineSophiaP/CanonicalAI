import pytest

from candidate_transformer.models.candidate import CandidateProfile
from candidate_transformer.validators import (
    validate_canonical_profile,
    validate_confidence,
    validate_projected_output,
    validate_required_fields,
)


def test_validate_canonical_profile_accepts_valid_profile():
    profile = CandidateProfile(candidate_id="c1", full_name="Jane Doe", overall_confidence=0.8)

    validated = validate_canonical_profile(profile)

    assert isinstance(validated, CandidateProfile)
    assert validated.candidate_id == "c1"


def test_validate_canonical_profile_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        validate_canonical_profile({"candidate_id": "c1", "overall_confidence": 1.2})


def test_validate_projected_output_checks_required_fields():
    projected = {"name": "Jane Doe", "email": "jane@example.com"}

    validate_projected_output(projected, required_fields=["name", "email"])

    with pytest.raises(ValueError):
        validate_projected_output({"name": "Jane Doe"}, required_fields=["name", "email"])


def test_validate_projected_output_checks_confidence_range():
    validate_projected_output({"name": "Jane Doe", "overall_confidence": 0.7})

    with pytest.raises(ValueError):
        validate_projected_output({"name": "Jane Doe", "overall_confidence": 1.2})


def test_validate_required_fields_rejects_missing_or_blank_values():
    validate_required_fields({"name": "Jane", "email": "jane@example.com"}, ["name", "email"])

    with pytest.raises(ValueError):
        validate_required_fields({"name": "Jane", "email": ""}, ["name", "email"])


def test_validate_confidence_range():
    validate_confidence(0.0)
    validate_confidence(0.5)
    validate_confidence(1.0)

    with pytest.raises(ValueError):
        validate_confidence(-0.1)

    with pytest.raises(ValueError):
        validate_confidence(1.1)
