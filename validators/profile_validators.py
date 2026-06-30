"""Validation helpers for canonical profiles and projected output."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

from models.candidate import CandidateProfile


def validate_confidence(value: Any, field_name: str = "confidence") -> float:
    """Validate that a confidence value is within the inclusive [0, 1] range."""
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc

    if numeric_value < 0.0 or numeric_value > 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1 inclusive")

    return numeric_value


def validate_required_fields(data: Mapping[str, Any], required_fields: Sequence[str]) -> None:
    """Ensure required fields exist and contain non-blank values."""
    for field_name in required_fields:
        value = data.get(field_name)
        if value is None:
            raise ValueError(f"missing required field: {field_name}")
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"required field is blank: {field_name}")


def validate_canonical_profile(profile: Any) -> CandidateProfile:
    """Validate a canonical profile object and return a CandidateProfile instance."""
    if isinstance(profile, CandidateProfile):
        candidate_profile = profile
    elif profile.__class__.__name__ == "CandidateProfile":
        # Convert duplicate namespace profile using model_dump or dict
        dump_func = getattr(profile, "model_dump", None) or getattr(profile, "dict", None)
        candidate_profile = CandidateProfile(**dump_func())
    else:
        candidate_profile = CandidateProfile(**profile)

    validate_confidence(candidate_profile.overall_confidence, field_name="overall_confidence")

    return candidate_profile


def validate_projected_output(
    data: Mapping[str, Any],
    required_fields: Optional[Sequence[str]] = None,
    field_specs: Optional[Sequence[Dict[str, Any]]] = None,
) -> Mapping[str, Any]:
    """Validate projected output values and optionally enforce required fields and types."""
    if required_fields:
        validate_required_fields(data, required_fields)

    if field_specs is not None:
        for field_spec in field_specs:
            output_key = field_spec.get("path")
            if output_key is None:
                continue

            if field_spec.get("required"):
                validate_required_fields(data, [output_key])

            expected_type = field_spec.get("type")
            if expected_type and output_key in data:
                _validate_type(output_key, data[output_key], expected_type)

    if "overall_confidence" in data:
        validate_confidence(data["overall_confidence"], field_name="overall_confidence")

    return data


def _validate_type(field_name: str, value: Any, expected_type: str) -> None:
    expected_type = expected_type.strip().lower()
    if expected_type == "string":
        if not isinstance(value, str) and value is not None:
            raise ValueError(f"field {field_name} must be a string")
    elif expected_type == "number":
        if not isinstance(value, (int, float)) and value is not None:
            raise ValueError(f"field {field_name} must be a number")
    elif expected_type == "string[]":
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"field {field_name} must be a list of strings")
    elif expected_type == "number[]":
        if not isinstance(value, list) or not all(isinstance(item, (int, float)) for item in value):
            raise ValueError(f"field {field_name} must be a list of numbers")
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"field {field_name} must be a boolean")
    elif expected_type == "object":
        if not isinstance(value, dict):
            raise ValueError(f"field {field_name} must be an object")
