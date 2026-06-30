"""Resume source adapter for TXT and PDF resumes."""
from __future__ import annotations

from pathlib import Path
from typing import List, Union
import logging

from inputs.source_adapter import SourceAdapter
from models.candidate import ParseResult
from parsers.resume_parser import parse_resume_text


class ResumeSourceAdapter(SourceAdapter):
    """Adapter to read resume files (.txt or .pdf).

    Produces a single ParseResult with `raw={'text': full_text}`.
    """

    def __init__(self, path: Union[str, Path]) -> None:
        super().__init__(path, source_name="resume")

    def read(self) -> List[ParseResult]:
        results: List[ParseResult] = []
        p = Path(self.path)
        if not p.exists():
            self.logger.warning("Resume file not found: %s", p)
            return results

        warnings: List[str] = []
        text = ""
        try:
            if p.suffix.lower() == ".pdf":
                try:
                    import pdfplumber

                    with pdfplumber.open(p) as pdf:
                        pages = [page.extract_text() or "" for page in pdf.pages]
                        text = "\n\n".join(pages)
                except Exception as e:  # pragma: no cover - pdf extraction
                    self.logger.exception("pdfplumber failed to extract text: %s", e)
                    warnings.append(f"pdf_extraction_failed: {e}")
            else:
                # treat as plain text
                text = p.read_text(encoding='utf-8')
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Failed to read resume %s: %s", p, exc)
            warnings.append(str(exc))

        if text:
            pr = parse_resume_text(text, source_path=str(p))
        else:
            pr = ParseResult(
                source="resume",
                raw={"text": text},
                warnings=warnings,
                metadata={"path": str(p)},
            )
        results.append(pr)
        return results
