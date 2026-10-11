"""
ERA: Event Resource & Administration System
Input Validation & Sanitization
"""

import re
from typing import Tuple

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")


def validate_email(email: str) -> bool:
    """Validates email format."""
    return bool(email and EMAIL_RE.fullmatch(email.strip()))


def validate_phone(phone: str) -> bool:
    """Validates 10-digit Indian mobile number."""
    if not phone:
        return False
    # Strip common prefixes like +91 or leading 0
    clean = re.sub(r"\D", "", phone)
    if clean.startswith("91") and len(clean) == 12:
        clean = clean[2:]
    return bool(PHONE_RE.fullmatch(clean))


def clean_phone(phone: str) -> str:
    """Cleans phone to 10 digits."""
    clean = re.sub(r"\D", "", phone or "")
    if clean.startswith("91") and len(clean) == 12:
        return clean[2:]
    return clean[-10:] if len(clean) >= 10 else clean


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validates strong password criteria:
    At least 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special character.
    """
    if not isinstance(password, str):
        return False, "Password must be a valid string."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "Password must contain at least one special character."
    return True, ""


def sanitize_string(val: str, max_length: int = 255) -> str:
    """Trims whitespace and bounds string length."""
    return (val or "").strip()[:max_length]
