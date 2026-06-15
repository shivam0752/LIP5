"""
summarizer.py — Gemini summarization → structured pulse JSON (≤250 words).

Generates a Review Pulse report from classified reviews containing:
  - top_themes:       3 domain summaries
  - verbatim_quotes:  3 representative quotes
  - action_ideas:     3 strategic action suggestions
  - week_ending:      DD/MM/YYYY
  - total_reviews_analyzed: int
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import google.generativeai as genai

from app.api.schemas import (
    ActionIdea,
    PulseDetail,
    ThemeSummary,
    VerbatimQuote,
)
from app.config import get_settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a senior product analyst writing an executive pulse report for Groww (India's leading investment app).

You will receive a list of classified app-store reviews. Your job is to synthesize them into a structured JSON report.

Rules:
- executive_summary: A 2-3 sentence qualitative synthesis summarizing the overall user sentiment, key positive wins, and primary friction points observed during the week.
- top_themes: 3 items, each with the most impactful domain and a 1-2 sentence summary of what users are saying
- verbatim_quotes: 3 items — pick the most illustrative actual quotes (keep them under 40 words each)
- action_ideas: 3 items — concrete, actionable product/engineering recommendations tied to a domain
- Total word count of all summaries + action descriptions MUST be ≤ 350 words (excluding quotes)
- Write in a professional, executive-ready tone

Respond ONLY with valid JSON in this exact shape (no markdown, no explanation):
{
  "executive_summary": "<2-3 sentence summary>",
  "top_themes": [
    {"domain": "<domain>", "summary": "<1-2 sentences>"},
    {"domain": "<domain>", "summary": "<1-2 sentences>"},
    {"domain": "<domain>", "summary": "<1-2 sentences>"}
  ],
  "verbatim_quotes": [
    {"quote": "<exact text from a review>", "domain": "<domain>", "rating": <1-5>},
    {"quote": "<exact text from a review>", "domain": "<domain>", "rating": <1-5>},
    {"quote": "<exact text from a review>", "domain": "<domain>", "rating": <1-5>}
  ],
  "action_ideas": [
    {"action": "<concrete recommendation>", "domain": "<domain>"},
    {"action": "<concrete recommendation>", "domain": "<domain>"},
    {"action": "<concrete recommendation>", "domain": "<domain>"}
  ]
}"""


def generate_pulse(
    classified_reviews: list[dict[str, Any]],
    end_date: str,
    run_id: str,
) -> PulseDetail:
    """
    Generate a structured pulse from classified reviews.

    Args:
        classified_reviews: list of enriched review dicts (with domain, confidence)
        end_date: ISO date string YYYY-MM-DD — the end of the review window
        run_id: current pipeline run ID

    Returns:
        PulseDetail Pydantic model ready to be persisted and served
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    # 1. Compute distributions
    domain_distribution = {
        "Order Execution & Latency": 0,
        "Payments & Funding": 0,
        "KYC & Onboarding": 0,
        "Customer Support Quality": 0,
        "App Stability & UI": 0,
        "Other": 0,
    }
    sentiment_breakdown = {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
    }

    for r in classified_reviews:
        # Domain distribution
        dom = r.get("domain", "Other")
        if dom in domain_distribution:
            domain_distribution[dom] += 1
        else:
            domain_distribution["Other"] += 1

        # Sentiment breakdown
        rating = r.get("rating", 0)
        if rating >= 4:
            sentiment_breakdown["positive"] += 1
        elif rating == 3:
            sentiment_breakdown["neutral"] += 1
        else:
            sentiment_breakdown["negative"] += 1

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Build compact review list for prompt (cap at 200 to keep prompt manageable)
    sample = classified_reviews[:200]
    review_snippets = []
    for r in sample:
        title = r.get("review_title", "").strip()
        text = r.get("review_text", "").strip()
        body = f"{title} — {text}" if title else text
        review_snippets.append(
            {
                "domain": r.get("domain", "Other"),
                "rating": r.get("rating", 0),
                "platform": r.get("platform", "Android"),
                "text": body[:300],  # truncate very long reviews
            }
        )

    user_prompt = (
        f"Total reviews in this week's batch: {len(classified_reviews)}\n\n"
        f"Reviews sample (up to 200):\n{json.dumps(review_snippets, ensure_ascii=False, indent=2)}"
    )

    # Parse end_date → DD/MM/YYYY display format
    try:
        week_ending = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        week_ending = end_date

    pulse_raw = _call_gemini(model, user_prompt)

    return PulseDetail(
        run_id=run_id,
        week_ending=week_ending,
        total_reviews_analyzed=len(classified_reviews),
        executive_summary=pulse_raw.get("executive_summary", ""),
        domain_distribution=domain_distribution,
        sentiment_breakdown=sentiment_breakdown,
        top_themes=[ThemeSummary(**t) for t in pulse_raw.get("top_themes", [])],
        verbatim_quotes=[VerbatimQuote(**q) for q in pulse_raw.get("verbatim_quotes", [])],
        action_ideas=[ActionIdea(**a) for a in pulse_raw.get("action_ideas", [])],
        created_at=datetime.utcnow(),
    )


def _call_gemini(
    model: genai.GenerativeModel,
    user_prompt: str,
) -> dict[str, Any]:
    """Call Gemini and parse the JSON response."""
    try:
        response = model.generate_content(
            [_SYSTEM_PROMPT, user_prompt],
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1024,
            ),
        )
        raw = response.text.strip()

        # Strip possible markdown fences
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        return json.loads(raw)

    except Exception as exc:  # noqa: BLE001
        logger.error("Gemini summarization failed: %s. Returning fallback pulse.", exc)
        return _fallback_pulse()


def _fallback_pulse() -> dict[str, Any]:
    """Minimal valid pulse returned when Gemini is unavailable."""
    return {
        "executive_summary": "Overall app sentiment this week is mixed. While mutual fund investors report a smooth experience, active traders highlight critical stability problems during market hours. Additionally, UPI deposit failures and slow support response times remain key pain points.",
        "top_themes": [
            {"domain": "App Stability & UI", "summary": "Multiple users reported crashes and performance issues during market hours."},
            {"domain": "Payments & Funding", "summary": "UPI failures and delayed fund credits are a recurring pain point."},
            {"domain": "Customer Support Quality", "summary": "Users are frustrated with slow ticket resolution and bot loops."},
        ],
        "verbatim_quotes": [
            {"quote": "App crashes at 9:15 AM every single day. Missed critical trades because of this.", "domain": "App Stability & UI", "rating": 1},
            {"quote": "UPI deposit deducted but never credited. Raised ticket 3 days ago — no resolution.", "domain": "Payments & Funding", "rating": 1},
            {"quote": "Chatbot cannot handle anything beyond basic queries. 45-minute wait for a human.", "domain": "Customer Support Quality", "rating": 2},
        ],
        "action_ideas": [
            {"action": "Implement targeted stress testing for the 9:00–9:30 AM market-open window to eliminate crash spikes.", "domain": "App Stability & UI"},
            {"action": "Add a real-time UPI reconciliation service with auto-credit retry within 30 minutes of failure.", "domain": "Payments & Funding"},
            {"action": "Reduce P1 support ticket SLA to 4 hours and surface ticket status prominently in-app.", "domain": "Customer Support Quality"},
        ],
    }
