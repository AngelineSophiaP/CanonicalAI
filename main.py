"""Command-line entrypoint for the candidate transformer."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent
PARENT_DIR = PROJECT_ROOT.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from candidate_transformer.inputs.csv_source_adapter import CSVSourceAdapter
from candidate_transformer.inputs.resume_source_adapter import ResumeSourceAdapter
from candidate_transformer.merger.merge_engine import MergeEngine
from candidate_transformer.projection.projector import Projector
from candidate_transformer.validators import validate_canonical_profile, validate_projected_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transform candidate CSV/resume inputs into a final profile JSON")
    parser.add_argument("--csv", required=True, help="Path to the recruiter CSV file")
    parser.add_argument("--resume", required=True, help="Path to the resume file")
    parser.add_argument("--config", required=True, help="Path to the JSON configuration file")
    parser.add_argument("--output", default="final_profile.json", help="Path to write the final profile JSON")
    return parser


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def get_projection_config(config: Dict[str, Any]) -> tuple[list[Dict[str, Any]], bool, bool, str]:
    fields = config.get("fields")
    projection = config.get("projection", {})

    if fields is not None:
        include_confidence = config.get("include_confidence", projection.get("include_confidence", True))
        include_provenance = config.get("include_provenance", projection.get("include_provenance", True))
        on_missing = config.get("on_missing", projection.get("on_missing", "null"))
        return fields if isinstance(fields, list) else [], include_confidence, include_provenance, on_missing

    include_confidence = projection.get("include_confidence", True)
    include_provenance = projection.get("include_provenance", True)
    on_missing = projection.get("on_missing", "null")
    fields = projection.get("fields", [])
    return fields if isinstance(fields, list) else [], include_confidence, include_provenance, on_missing


def build_projection_specs(fields: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    specs: list[Dict[str, Any]] = []
    for field in fields:
        if isinstance(field, str):
            specs.append({"path": field, "from": field})
            continue

        if not isinstance(field, dict):
            continue

        output_key = field.get("output") or field.get("name") or field.get("path")
        if not output_key:
            continue

        source_path = field.get("from") or field.get("source") or output_key
        spec: Dict[str, Any] = {"path": output_key, "from": source_path}
        for key in ("normalize", "on_missing", "required", "type"):
            if key in field:
                spec[key] = field[key]
        specs.append(spec)
    return specs


def build_default_projection_specs() -> list[Dict[str, Any]]:
    default_fields = [
        "candidate_id",
        "full_name",
        "emails",
        "phones",
        "location",
        "links",
        "headline",
        "years_experience",
        "skills",
        "experience",
        "education",
        "provenance",
        "overall_confidence",
    ]
    return [{"path": field, "from": field} for field in default_fields]


def to_json_compatible(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): to_json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_json_compatible(item) for item in value]
    if isinstance(value, BaseModel):
        if hasattr(value, "model_dump"):
            return to_json_compatible(value.model_dump())
        return to_json_compatible(value.dict())
    if isinstance(value, Path):
        return str(value)
    return str(value)


def project_profile(profile: Any, config: Dict[str, Any]) -> Dict[str, Any]:
    fields, include_confidence, include_provenance, on_missing = get_projection_config(config)
    projection_specs = build_projection_specs(fields)
    if not projection_specs:
        projection_specs = build_default_projection_specs()

    projector = Projector(projection_specs, default_on_missing=on_missing)
    projected = projector.project(profile)

    if include_confidence and "overall_confidence" not in projected:
        projected["overall_confidence"] = getattr(profile, "overall_confidence", None)

    if include_provenance and "provenance" not in projected:
        projected["provenance"] = getattr(profile, "provenance", None)

    return to_json_compatible(projected)


def run_pipeline(csv_path: Path, resume_path: Path, config_path: Path, output_path: Path) -> int:
    config = load_config(config_path)

    csv_adapter = CSVSourceAdapter(csv_path)
    resume_adapter = ResumeSourceAdapter(resume_path)

    parse_results = []
    parse_results.extend(csv_adapter.read())
    parse_results.extend(resume_adapter.read())

    merge_engine = MergeEngine()
    candidate_id = csv_path.stem or "candidate"
    profile = merge_engine.merge(parse_results, candidate_id=candidate_id)
    validated_profile = validate_canonical_profile(profile)

    fields, _, _, _ = get_projection_config(config)
    projection_specs = build_projection_specs(fields)

    projected = project_profile(validated_profile, config)
    required_fields = [field for field in ["full_name", "emails"] if field in projected]
    validate_projected_output(projected, required_fields=required_fields, field_specs=projection_specs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(projected, handle, indent=2)
        handle.write("\n")

    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        csv_path = Path(args.csv).expanduser().resolve()
        resume_path = Path(args.resume).expanduser().resolve()
        config_path = Path(args.config).expanduser().resolve()
        output_path = Path(args.output).expanduser().resolve()

        for label, path in (("CSV file", csv_path), ("resume file", resume_path), ("config file", config_path)):
            if not path.exists():
                raise FileNotFoundError(f"{label} not found: {path}")

        return run_pipeline(csv_path, resume_path, config_path, output_path)
    except Exception as exc:  # pragma: no cover - defensive CLI error handling
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
