"""Phone number normalization to E.164 using phonenumbers."""
from __future__ import annotations

from typing import Optional
import phonenumbers
import re


def normalize_phone(number: Optional[str], default_region: str = "US") -> Optional[str]:
    """Normalize a phone number string to strict E.164.

    Returns normalized E.164 or None for invalid/empty inputs.
    """
    if not number:
        return None
    s = str(number).strip()
    if not s:
        return None

    # Check that we have at least 7 digits total
    digits = re.sub(r"[^0-9]", "", s)
    if len(digits) < 7:
        return None

    # Remove all non-digits except a leading '+'.
    if "+" in s:
        sanitized = "+" + digits
        return sanitized

    sanitized = digits

    # Parse non-international numbers with default region.
    try:
        parsed = phonenumbers.parse(sanitized, default_region)
    except phonenumbers.NumberParseException:
        return None

    if not phonenumbers.is_valid_number(parsed):
        return None

    formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    if not re.fullmatch(r"\+[0-9]+", formatted):
        return None

    return formatted
