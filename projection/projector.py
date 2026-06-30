"""Projection utilities for mapping candidate data to a target shape."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from normalizers.date_normalizer import normalize_date_to_yyyy_mm
from normalizers.phone_normalizer import normalize_phone
from normalizers.skill_normalizer import normalize_skill
from projection.path_resolver import PathResolver


class Projector:
    """Project candidate data using a runtime field specification."""

    def __init__(
        self,
        field_specs: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
        default_on_missing: str = "null",
    ):
        self.default_on_missing = default_on_missing
        self.field_specs = self._normalize_field_specs(field_specs)

    def _normalize_field_specs(self, field_specs: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if field_specs is None:
            return []
        if isinstance(field_specs, dict):
            normalized: List[Dict[str, Any]] = []
            for output_key, spec in field_specs.items():
                if isinstance(spec, str):
                    normalized.append({"path": output_key, "from": spec})
                elif isinstance(spec, dict):
                    source_path = spec.get("from") or spec.get("source") or spec.get("path") or output_key
                    field: Dict[str, Any] = {
                        "path": output_key,
                        "from": source_path,
                        "on_missing": spec.get("on_missing", self.default_on_missing),
                        "normalize": spec.get("normalize"),
                    }
                    normalized.append(field)
                else:
                    normalized.append({"path": output_key, "from": output_key})
            return normalized
        if isinstance(field_specs, list):
            return [field for field in field_specs if isinstance(field, dict)]
        return []

    def project(self, data: Any) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for spec in self.field_specs:
            output_key = spec.get("path")
            if not output_key:
                continue

            source_path = spec.get("from", output_key)
            on_missing = spec.get("on_missing", self.default_on_missing)

            try:
                value = PathResolver(source_path).resolve(data, on_missing=on_missing)
            except KeyError as exc:
                if on_missing == "error":
                    raise ValueError(f"required field missing: {output_key}") from exc
                if on_missing == "omit":
                    continue
                value = None

            if value is None:
                if on_missing == "omit":
                    continue
                if on_missing == "error":
                    raise ValueError(f"required field missing: {output_key}")
                result[output_key] = None
                continue

            result[output_key] = self._apply_normalization(value, spec.get("normalize"))

        return result

    def _apply_normalization(self, value: Any, normalize: Optional[str]) -> Any:
        if normalize is None:
            return value

        normalized_type = str(normalize).strip().lower()
        if normalized_type == "e164":
            return self._normalize_e164(value)
        if normalized_type == "canonical":
            return self._normalize_canonical(value)
        if normalized_type == "date":
            return self._normalize_date(value)

        return value

    def _normalize_e164(self, value: Any) -> Any:
        if isinstance(value, list):
            normalized = [normalize_phone(item) for item in value]
            return [item for item in normalized if item is not None]
        return normalize_phone(value)

    def _normalize_canonical(self, value: Any) -> Any:
        if isinstance(value, list):
            normalized = [normalize_skill(item) for item in value]
            return [item for item in normalized if item is not None]
        return normalize_skill(value)

    def _normalize_date(self, value: Any) -> Any:
        if isinstance(value, list):
            normalized = [normalize_date_to_yyyy_mm(item) for item in value]
            return [item for item in normalized if item is not None]
        return normalize_date_to_yyyy_mm(value)
