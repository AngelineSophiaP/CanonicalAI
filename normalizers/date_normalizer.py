"""Date normalization utilities using python-dateutil.

Converts date-like strings to YYYY-MM when month information is present.
Never invent months when only a year is provided.
"""
from __future__ import annotations

from typing import Optional
import re
from dateutil import parser


def normalize_date_to_yyyy_mm(value: Optional[str]) -> Optional[str]:
    """Normalize a date string to YYYY-MM if month information is present.

    If input is a bare year (e.g. "2020"), returns None (do not invent months).
    Returns None for empty or unparseable inputs.
    """
    if not value:
        return None
    s = value.strip()
    if not s:
        return None

    # If it's exactly a 4-digit year, do not invent a month
    if re.fullmatch(r"\d{4}", s):
        return None

    # Accept month names (full or abbreviated) and month-number formats.
    has_month_name = re.search(
        r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
        s,
        re.I,
    )
    has_month_number = bool(
        re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", s)
        or re.search(r"\b\d{1,2}[/-]\d{4}\b", s)
        or re.search(r"\b\d{4}[/-]\d{1,2}\b", s)
    )

    if not (has_month_name or has_month_number):
        return None

    try:
        dt = parser.parse(s, fuzzy=True)
    except Exception:
        return None

    if dt.month is None:
        return None

    return f"{dt.year:04d}-{dt.month:02d}"
