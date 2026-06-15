"""
conftest.py — Shared pytest fixtures for LIP5 backend tests.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# ── Env stub so config loads without real credentials ─────────────────────────


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject stub environment variables so Settings can be instantiated."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRETS_FILE", "credentials.json")
    monkeypatch.setenv("GROWW_PACKAGE_NAME", "com.nextbillion.groww")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")


@pytest.fixture()
def tmp_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Override DATA_DIR to a temp directory for isolation."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # Clear cached settings so new DATA_DIR takes effect
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    yield tmp_path
    get_settings.cache_clear()  # type: ignore[attr-defined]


# ── Sample review fixtures ─────────────────────────────────────────────────────

@pytest.fixture()
def sample_reviews() -> list[dict]:
    return [
        {
            "rating": 1,
            "review_title": "App crashes constantly",
            "review_text": "The app crashes every morning at 9 AM when markets open. Very frustrating.",
            "date": "2024-06-01",
            "platform": "Android",
        },
        {
            "rating": 2,
            "review_title": "UPI payment failed",
            "review_text": "My UPI transfer was deducted but never credited to my Groww account. Raised a ticket but no response.",
            "date": "2024-06-02",
            "platform": "iOS",
        },
        {
            "rating": 5,
            "review_title": "Great investment app",
            "review_text": "Best investment app in India. Very smooth experience for buying mutual funds.",
            "date": "2024-06-03",
            "platform": "Android",
        },
        {
            "rating": 1,
            "review_title": "KYC stuck",
            "review_text": "My KYC has been pending for two weeks. Documents uploaded but verification never completed.",
            "date": "2024-06-04",
            "platform": "iOS",
        },
        {
            "rating": 3,
            "review_title": "Support is slow",
            "review_text": "The customer support chatbot cannot resolve anything beyond basic queries. Had to wait 2 hours.",
            "date": "2024-06-05",
            "platform": "Android",
        },
    ]


@pytest.fixture()
def classified_reviews(sample_reviews: list[dict]) -> list[dict]:
    domains = [
        "App Stability & UI",
        "Payments & Funding",
        "App Stability & UI",
        "KYC & Onboarding",
        "Customer Support Quality",
    ]
    return [
        {**r, "id": i, "domain": domains[i], "confidence": "high"}
        for i, r in enumerate(sample_reviews)
    ]
