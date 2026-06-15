"""
sanitizer.py — PII regex engine for review text.

Patterns sanitized (replaced with [REDACTED]):
  - Email addresses
  - Indian mobile phone numbers (10-digit starting 6-9)
  - UPI IDs (name@provider handles)
  - PAN card numbers (ABCDE1234F format)
  - Aadhaar numbers (12-digit, space-separated or plain)
  - Tracker strings / internal IDs (16+ char alphanumeric)

Reviews with < 10 characters of body text after sanitization are discarded.
"""

from __future__ import annotations

import re
from typing import Any

# ── Regex patterns ─────────────────────────────────────────────────────────────

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Email
    ("email", re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        re.IGNORECASE,
    )),
    # UPI ID must come BEFORE email because UPI is a sub-pattern of email-like strings
    # but we handle UPI specifically by its known provider suffixes
    ("upi", re.compile(
        r"[a-zA-Z0-9.\-_]+@(?:okicici|okhdfcbank|okaxis|oksbi|ybl|ibl|axl|"
        r"paytm|upi|apl|yapl|naviapp|fbl|rbl|jsb|aubank|indus|barodampay|"
        r"ikwik|pingpay|slice|jupiter|fi|lime|kotak|icici|sbi|hdfc|axis|"
        r"federal|union|pnb|bob|cbi|idfc|idbi|yes|bandhan|airtel|jio|"
        r"wajirock|wajirock)",
        re.IGNORECASE,
    )),
    # Indian phone — 10 digits starting 6-9, optionally prefixed +91 or 0
    ("phone", re.compile(
        r"(?<!\d)(?:\+91|0)?[6-9]\d{9}(?!\d)"
    )),
    # PAN card — exactly 5 letters, 4 digits, 1 letter
    ("pan", re.compile(
        r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
    )),
    # Aadhaar — 12 digits (with optional spaces every 4 digits)
    ("aadhaar", re.compile(
        r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"
    )),
    # Tracker / internal ID — 16+ char alphanumeric token
    ("tracker", re.compile(
        r"\b[A-Za-z0-9]{16,}\b"
    )),
]

_REDACTED = "[REDACTED]"
_MIN_BODY_LENGTH = 10


def sanitize_text(text: str) -> str:
    """Apply all PII patterns to a single string and return the cleaned version."""
    for _name, pattern in _PATTERNS:
        text = pattern.sub(_REDACTED, text)
    return text.strip()


def sanitize_review(review: dict[str, Any]) -> dict[str, Any] | None:
    """
    Sanitize a single review dict in-place (copies).
    Returns None if the body is too short after sanitization.
    """
    cleaned = dict(review)
    cleaned["review_title"] = sanitize_text(review.get("review_title") or "")
    cleaned["review_text"] = sanitize_text(review.get("review_text") or "")
    if len(cleaned["review_text"]) < _MIN_BODY_LENGTH:
        return None
    return cleaned


def sanitize_reviews(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sanitize an entire list of review dicts.
    Discards reviews whose body is < 10 chars after PII removal.
    """
    result: list[dict[str, Any]] = []
    for review in reviews:
        cleaned = sanitize_review(review)
        if cleaned is not None:
            result.append(cleaned)
    return result
