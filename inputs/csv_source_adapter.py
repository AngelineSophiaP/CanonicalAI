"""CSV source adapter for recruiter CSVs."""
from __future__ import annotations

from pathlib import Path
from typing import List, Union
import csv
import logging

from inputs.source_adapter import SourceAdapter
from models.candidate import ParseResult


class CSVSourceAdapter(SourceAdapter):
    """Adapter to read recruiter CSV files.

    Expects columns: name, email, phone, current_company, title
    """

    def __init__(self, path: Union[str, Path]) -> None:
        super().__init__(path, source_name="csv")

    def read(self) -> List[ParseResult]:
        results: List[ParseResult] = []
        p = Path(self.path)
        if not p.exists():
            self.logger.warning("CSV file not found: %s", p)
            return results

        try:
            with p.open(newline='', encoding='utf-8') as fh:
                reader = csv.DictReader(fh)
                for idx, row in enumerate(reader):
                    warnings: List[str] = []
                    # normalize keys to expected names (lowercase) and strip values
                    normalized_row = {k.strip().lower(): (v.strip() if v is not None else v) for k, v in row.items() if k is not None}
                    # attach warning if minimal fields missing
                    if not normalized_row.get('email') and not normalized_row.get('phone'):
                        warnings.append('missing contact info: email and phone both empty')

                    pr = ParseResult(
                        source="csv",
                        raw=normalized_row,
                        warnings=warnings,
                        metadata={"path": str(p), "row": idx},
                    )
                    results.append(pr)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Failed to read CSV %s: %s", p, exc)

        return results
