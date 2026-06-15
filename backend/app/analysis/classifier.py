"""
classifier.py — Batch Gemini classification of reviews into 5 fintech domains.

Uses Gemini 1.5 Flash to classify each sanitized review into one of:
  1. Order Execution & Latency
  2. Payments & Funding
  3. KYC & Onboarding
  4. Customer Support Quality
  5. App Stability & UI
  6. Other (fallback)

Processes reviews in batches of 50 to stay within API limits.
Output per review: { id, domain, confidence, rating, review_text, date, platform }
"""

from __future__ import annotations

import json
import logging
from typing import Any

import google.generativeai as genai

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Domain constants ────────────────────────────────────────────────────────────

DOMAINS = [
    "Order Execution & Latency",
    "Payments & Funding",
    "KYC & Onboarding",
    "Customer Support Quality",
    "App Stability & UI",
    "Other",
]

_SYSTEM_PROMPT = """You are a fintech product analyst classifying app-store reviews for Groww (India's leading investment app).

For each review, assign exactly ONE domain from this list:
1. Order Execution & Latency — options slippage, delayed limit orders, chart mismatches, P&L errors
2. Payments & Funding — bank deposits, UPI failures, withdrawal delays, settlement cycles
3. KYC & Onboarding — account creation, re-KYC, document/PAN/Aadhaar verification
4. Customer Support Quality — agent responsiveness, bot loops, ticket resolution time
5. App Stability & UI — post-update crashes, freezes at market open, biometric login bugs, UI misalignment
6. Other — anything that doesn't fit cleanly into the above

Also rate your confidence as: high, medium, or low.

Respond ONLY with a valid JSON array. Each element must be:
{"id": <int>, "domain": "<domain name>", "confidence": "<high|medium|low>"}

Do not include any explanation or markdown."""


def classify_reviews(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Classify a list of sanitized reviews using Gemini.

    Args:
        reviews: list of dicts with keys: rating, review_title, review_text, date, platform

    Returns:
        list of enriched dicts adding: domain, confidence, id
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Assign sequential IDs to reviews
    indexed = [{"id": i, **r} for i, r in enumerate(reviews)]

    # Process in batches of 50
    batch_size = 50
    classifications: dict[int, dict[str, str]] = {}

    for batch_start in range(0, len(indexed), batch_size):
        batch = indexed[batch_start : batch_start + batch_size]
        batch_results = _classify_batch(model, batch)
        classifications.update(batch_results)
        logger.info(
            "Classified batch %d–%d (%d/%d total)",
            batch_start,
            batch_start + len(batch) - 1,
            min(batch_start + batch_size, len(indexed)),
            len(indexed),
        )

    # Merge classification results back into reviews
    enriched: list[dict[str, Any]] = []
    for item in indexed:
        cls = classifications.get(item["id"], {"domain": "Other", "confidence": "low"})
        enriched.append(
            {
                **item,
                "domain": cls.get("domain", "Other"),
                "confidence": cls.get("confidence", "low"),
            }
        )

    return enriched


def _classify_batch(
    model: genai.GenerativeModel,
    batch: list[dict[str, Any]],
) -> dict[int, dict[str, str]]:
    """Send one batch of reviews to Gemini and return {id: {domain, confidence}}."""
    # Build compact review list for the prompt
    review_lines = []
    for item in batch:
        title = item.get("review_title", "").strip()
        text = item.get("review_text", "").strip()
        rating = item.get("rating", 0)
        combined = f"{title} — {text}" if title else text
        review_lines.append(
            f'{{"id": {item["id"]}, "rating": {rating}, "text": {json.dumps(combined)}}}'
        )

    user_prompt = "Classify these reviews:\n[\n" + ",\n".join(review_lines) + "\n]"

    try:
        response = model.generate_content(
            [_SYSTEM_PROMPT, user_prompt],
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )
        raw = response.text.strip()

        # Strip possible markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        parsed: list[dict[str, Any]] = json.loads(raw)
        return {
            item["id"]: {
                "domain": _validate_domain(item.get("domain", "Other")),
                "confidence": item.get("confidence", "low"),
            }
            for item in parsed
            if "id" in item
        }

    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini classification failed for batch: %s. Falling back to 'Other'.", exc)
        return {item["id"]: {"domain": "Other", "confidence": "low"} for item in batch}


def _validate_domain(domain: str) -> str:
    """Ensure domain string matches one of the 6 valid domains."""
    for valid in DOMAINS:
        if valid.lower() == domain.strip().lower():
            return valid
    # Fuzzy partial match
    for valid in DOMAINS:
        if valid.lower().split("&")[0].strip() in domain.lower():
            return valid
    return "Other"
