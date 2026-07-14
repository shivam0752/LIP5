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

For each review, assign exactly ONE domain from this exact list:
1. "Order Execution & Latency"
2. "Payments & Funding"
3. "KYC & Onboarding"
4. "Customer Support Quality"
5. "App Stability & UI"
6. "Other"

Also rate your confidence as: high, medium, or low.

Respond ONLY with a valid JSON array. Each element must be:
{"id": <int>, "domain": "<exact domain name from the list above>", "confidence": "<high|medium|low>"}

Do not include any explanation, markdown, or any trailing descriptions in the domain name."""


def classify_reviews(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Classify a list of sanitized reviews using Gemini. Falls back to a heuristic
    rule-based classifier if Gemini is unavailable or not configured.

    Args:
        reviews: list of dicts with keys: rating, review_title, review_text, date, platform

    Returns:
        list of enriched dicts adding: domain, confidence, id
    """
    settings = get_settings()
    
    if not settings.gemini_api_key:
        from app.storage.store import append_log
        append_log("GEMINI_API_KEY is not configured. Using rule-based heuristic classifier.", level="WARNING")
        enriched: list[dict[str, Any]] = []
        for i, r in enumerate(reviews):
            dom = _heuristic_classify(r.get("review_text", ""), r.get("review_title", ""))
            enriched.append({
                "id": i,
                **r,
                "domain": dom,
                "confidence": "medium",
            })
        return enriched

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
    enriched = []
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
        logger.warning("Gemini classification failed for batch: %s. Falling back to heuristic classifier.", exc)
        return {
            item["id"]: {
                "domain": _heuristic_classify(item.get("review_text", ""), item.get("review_title", "")),
                "confidence": "medium",
            }
            for item in batch
        }


def _heuristic_classify(review_text: str, review_title: str) -> str:
    """Classify a review based on keyword heuristics when Gemini is unavailable."""
    text = (review_title + " " + review_text).lower()

    # 1. Order Execution & Latency
    if any(k in text for k in ["option", "slippage", "limit order", "market order", "execution", "latency", "chart", "ltp", "price", "trade", "buy", "sell"]):
        return "Order Execution & Latency"
    # 2. Payments & Funding
    if any(k in text for k in ["upi", "deposit", "money", "bank", "fund", "credit", "transaction", "payment", "ledger", "withdraw", "neft", "rtgs", "pay"]):
        return "Payments & Funding"
    # 3. KYC & Onboarding
    if any(k in text for k in ["kyc", "onboard", "verify", "aadhaar", "pan", "document", "selfie", "account creation", "register", "signup"]):
        return "KYC & Onboarding"
    # 4. Customer Support Quality
    if any(k in text for k in ["support", "ticket", "help", "agent", "bot", "customer care", "respond", "reply", "chat"]):
        return "Customer Support Quality"
    # 5. App Stability & UI
    if any(k in text for k in ["crash", "freeze", "hang", "slow", "update", "ui", "screen", "dark mode", "lag", "bug", "stuck", "open"]):
        return "App Stability & UI"

    return "Other"


def _validate_domain(domain: str) -> str:
    """Ensure domain string matches one of the 6 valid domains."""
    for valid in DOMAINS:
        if valid.lower() == domain.strip().lower():
            return valid
    # Fuzzy partial match
    for valid in DOMAINS:
        if valid.lower() in domain.lower():
            return valid
    for valid in DOMAINS:
        if valid.lower().split("&")[0].strip() in domain.lower():
            return valid
    return "Other"
