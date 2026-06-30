"""CSV parser for recruiter CSV files.

Provides a `parse_csv` function that reads a CSV file and returns a list
of `ParseResult` instances with standardized keys.
"""
from __future__ import annotations

from pathlib import Path
from typing import List
import csv
import logging

from models.candidate import ParseResult


LOGGER = logging.getLogger("candidate_transformer.parsers.csv_parser")


def parse_csv(path: str) -> List[ParseResult]:
    """Parse recruiter CSV and return list of ParseResult.

    Expected columns (case-insensitive): name, email, phone, current_company, title
    Returns an empty list if file is missing or unreadable.
    """
    results: List[ParseResult] = []
    p = Path(path)
    if not p.exists():
        LOGGER.warning("CSV file not found: %s", p)
        return results

    try:
        with p.open(newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            for idx, row in enumerate(reader):
                warnings: List[str] = []
                # normalize keys to lowercase
                normalized = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}

                # map to expected keys
                mapped = {
                    "name": normalized.get("name") or normalized.get("full_name"),
                    "email": normalized.get("email"),
                    "phone": normalized.get("phone"),
                    "current_company": normalized.get("current_company") or normalized.get("company"),
                    "title": normalized.get("title") or normalized.get("job_title"),
                }

                if not mapped.get("email") and not mapped.get("phone"):
                    warnings.append("missing contact info: email and phone both empty")

                pr = ParseResult(
                    source="csv",
                    raw=mapped,
                    warnings=warnings,
                    metadata={"path": str(p), "row": idx},
                )
                results.append(pr)
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.exception("Failed to parse CSV %s: %s", p, exc)

    return results
