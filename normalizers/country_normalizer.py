"""Country normalization to ISO-3166 alpha-2 with a small builtin map."""
from __future__ import annotations

from typing import Optional
import re

# Minimal mapping for common country names/aliases. Expandable.
_COUNTRY_MAP = {
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
    "us": "US",
    "united kingdom": "GB",
    "uk": "GB",
    "great britain": "GB",
    "gb": "GB",
    "germany": "DE",
    "de": "DE",
    "france": "FR",
    "fr": "FR",
    "canada": "CA",
    "ca": "CA",
    "australia": "AU",
    "au": "AU",
    "india": "IN",
    "in": "IN",
}


def normalize_country(value: Optional[str]) -> Optional[str]:
    """Normalize country names/abbreviations to ISO-3166 alpha-2.

    Returns None for unknown or empty inputs.
    """
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None

    # If already looks like a 2-letter code, use the built-in mapping when available.
    if re.fullmatch(r"[A-Za-z]{2}", s):
        mapped = _COUNTRY_MAP.get(s.lower())
        if mapped:
            return mapped
        return s.upper()

    key = s.lower()
    key = re.sub(r"[^a-z ]", " ", key)
    key = re.sub(r"\s+", " ", key).strip()
    return _COUNTRY_MAP.get(key)
