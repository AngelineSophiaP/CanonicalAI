"""Skill normalization and canonicalization utilities."""
from __future__ import annotations

from typing import Optional
import re

_CANONICAL_MAP = {
    "py": "Python",
    "python": "Python",
    "python programming": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "node": "JavaScript",
    "node.js": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "c plus plus": "C++",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "sql": "SQL",
    "golang": "Go",
    "go": "Go",
    "rb": "Ruby",
    "ruby": "Ruby",
    "java": "Java",
}


def _normalize_key(s: str) -> str:
    s2 = s.lower()
    s2 = re.sub(r"[^a-z0-9#+ ]", " ", s2)
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2


def normalize_skill(skill: Optional[str]) -> Optional[str]:
    """Normalize a raw skill string to a canonical skill name when possible.

    For known variants (see _CANONICAL_MAP) returns canonical name. For unknown
    but non-empty values, returns a cleaned, title-cased version.
    Returns None for empty inputs.
    """
    if not skill:
        return None
    s = str(skill).strip()
    if not s:
        return None

    key = _normalize_key(s)
    if key in _CANONICAL_MAP:
        return _CANONICAL_MAP[key]

    # Otherwise, produce a cleaned title-cased version (do not invent)
    cleaned = re.sub(r"[^A-Za-z0-9+# ]", " ", s)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None

    # Title-case common connectors but preserve C++/C#/SQL-like tokens
    if cleaned.lower() in ("c++", "c#", "sql"):
        return cleaned
    return cleaned.title()
