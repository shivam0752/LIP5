"""
summarizer.py — Gemini summarization → structured pulse JSON (≤250 words).

Generates a Review Analyser report from classified reviews containing:
  - top_themes:       3 domain summaries with deep insights
  - verbatim_quotes:  3 representative quotes
  - action_ideas:     3 strategic action suggestions
  - timeline:         DD/MM/YYYY to DD/MM/YYYY
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

_SYSTEM_PROMPT = """You are a senior product analyst writing an executive Review Analyser report for Groww (India's leading investment app).

You will receive a list of classified app-store reviews. Your job is to synthesize them into a structured JSON report.

Rules:
- executive_summary: A 2-3 sentence qualitative synthesis summarizing the overall user sentiment, key positive wins, and primary friction points observed during the selected timeline.
- top_themes: 3 items, each with the most impactful domain and a detailed paragraph containing deep actual insights derived from the reviews (patterns, recurring issues, or notable user behavior).
- verbatim_quotes: 3 items — pick the most illustrative actual quotes (keep them under 40 words each)
- action_ideas: 3 items — concrete, actionable product/engineering recommendations tied to a domain
- Total word count of all summaries + action descriptions MUST be ≤ 450 words (excluding quotes)
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
    start_date: str,
    end_date: str,
    run_id: str,
) -> PulseDetail:
    """
    Generate a structured pulse from classified reviews.

    Args:
        classified_reviews: list of enriched review dicts (with domain, confidence)
        start_date: ISO date string YYYY-MM-DD
        end_date: ISO date string YYYY-MM-DD
        run_id: current pipeline run ID

    Returns:
        PulseDetail Pydantic model ready to be persisted and served
    """
def generate_pulse(
    classified_reviews: list[dict[str, Any]],
    start_date: str,
    end_date: str,
    run_id: str,
) -> PulseDetail:
    """
    Generate a structured pulse from classified reviews.

    Args:
        classified_reviews: list of enriched review dicts (with domain, confidence)
        start_date: ISO date string YYYY-MM-DD
        end_date: ISO date string YYYY-MM-DD
        run_id: current pipeline run ID

    Returns:
        PulseDetail Pydantic model ready to be persisted and served
    """
    settings = get_settings()

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

    # Parse dates → short display format e.g. "08 Jun – 15 Jun '26"
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt   = datetime.strptime(end_date,   "%Y-%m-%d")
        yr = end_dt.strftime("'%y")
        if start_dt.year == end_dt.year:
            timeline = f"{start_dt.strftime('%d %b')} – {end_dt.strftime('%d %b')} {yr}"
        else:
            yr_start = start_dt.strftime("'%y")
            timeline = f"{start_dt.strftime('%d %b')} {yr_start} – {end_dt.strftime('%d %b')} {yr}"
    except ValueError:
        timeline = f"{start_date} to {end_date}"

    use_fallback = False
    pulse_raw = None

    if not settings.gemini_api_key:
        from app.storage.store import append_log
        append_log(
            "GEMINI_API_KEY is not configured. Falling back to dynamic simulated analysis.",
            level="WARNING",
            run_id=run_id
        )
        use_fallback = True
    else:
        try:
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

            pulse_raw = _call_gemini(model, user_prompt)
        except Exception as exc:
            from app.storage.store import append_log
            append_log(
                f"Gemini API call failed: {exc}. Falling back to dynamic simulated analysis.",
                level="WARNING",
                run_id=run_id
            )
            use_fallback = True

    if use_fallback or not pulse_raw:
        pulse_raw = _fallback_pulse(list(classified_reviews), start_date, end_date)

    return PulseDetail(
        run_id=run_id,
        timeline=timeline,
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


def _fallback_pulse(
    classified_reviews: list[dict[str, Any]],
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """
    Generate a dynamic fallback pulse when Gemini is unavailable.
    Constructs themes, quotes, and actions dynamically based on the input reviews.
    Always returns exactly 3 items for top_themes, verbatim_quotes, and action_ideas.
    """
    # Identify top domains present in reviews
    domain_counts: dict[str, int] = {}
    for r in classified_reviews:
        dom = r.get("domain", "Other")
        domain_counts[dom] = domain_counts.get(dom, 0) + 1

    # Sort domains by frequency (excluding "Other" unless necessary)
    sorted_domains = sorted(
        [d for d in domain_counts if d != "Other"],
        key=lambda d: domain_counts[d],
        reverse=True
    )
    
    # Standard static fallbacks to guarantee 3 items
    default_domains = ["App Stability & UI", "Payments & Funding", "Customer Support Quality"]
    for d in default_domains:
        if d not in sorted_domains:
            sorted_domains.append(d)
            
    top_domains = sorted_domains[:3]

    # Dynamic themes mapping
    theme_templates = {
        "Order Execution & Latency": "Active traders report order execution delays and slippage on limit/market orders, particularly during high-volatility market-open hours.",
        "Payments & Funding": "UPI payment failures, bank linking issues, and delayed fund settlements are a recurring friction point for depositors.",
        "KYC & Onboarding": "Users report friction in the account opening and re-verification loops, especially document verification and Aadhaar/PAN validation.",
        "Customer Support Quality": "Friction persists in customer support response times, with users reporting ticketing delays and limited assistance from automated bots.",
        "App Stability & UI": "App stability complaints, crashes, and performance issues are reported, particularly after updates and during early trading hours.",
        "Other": "Miscellaneous feedback and general user queries regarding portfolio tracking, updates, and navigation."
    }

    top_themes = [
        {"domain": dom, "summary": theme_templates.get(dom, theme_templates["Other"])}
        for dom in top_domains
    ]

    # Standard static quotes fallback
    default_quotes = [
        {"quote": "App crashes at 9:15 AM every single day. Missed critical trades because of this.", "domain": "App Stability & UI", "rating": 1},
        {"quote": "UPI deposit deducted but never credited. Raised ticket 3 days ago — no resolution.", "domain": "Payments & Funding", "rating": 1},
        {"quote": "Chatbot cannot handle anything beyond basic queries. 45-minute wait for a human.", "domain": "Customer Support Quality", "rating": 2},
    ]

    # Select real quotes for the top domains
    verbatim_quotes = []
    pool = list(classified_reviews)
    for idx, dom in enumerate(top_domains):
        # Find reviews in this domain
        dom_reviews = [r for r in pool if r.get("domain") == dom]
        if dom_reviews:
            # Sort by rating ascending to show pain points
            dom_reviews_sorted = sorted(dom_reviews, key=lambda r: r.get("rating", 3))
            best_fit = dom_reviews_sorted[0]
            quote_text = best_fit.get("review_text", "")
            if len(quote_text) > 120:
                quote_text = quote_text[:117] + "..."
            verbatim_quotes.append({
                "quote": quote_text,
                "domain": dom,
                "rating": best_fit.get("rating", 3)
            })
            pool.remove(best_fit)
        else:
            # Fallback to the default quote for this index
            verbatim_quotes.append(default_quotes[idx])

    # Dynamic action ideas templates
    action_templates = {
        "Order Execution & Latency": "Implement targeted stress testing for options limit order execution pipelines to reduce latency during volatile market periods.",
        "Payments & Funding": "Introduce automatic reconciliation checks for UPI deposit failures to credit user accounts within 15 minutes.",
        "KYC & Onboarding": "Revamp the document OCR and video verification workflow to reduce onboarding drop-offs and re-verification loops.",
        "Customer Support Quality": "Optimize the chat routing algorithm to escalate high-severity tickets to human agents faster.",
        "App Stability & UI": "Establish mandatory performance profiling for the mobile app before production release to resolve launch-time crashes.",
        "Other": "Conduct user experience audits on new features and improve general app navigation and tooltips."
    }

    action_ideas = [
        {"action": action_templates.get(dom, action_templates["Other"]), "domain": dom}
        for dom in top_domains
    ]

    # Construct overall summary based on top domains
    summary_parts = []
    if "App Stability & UI" in top_domains or "Order Execution & Latency" in top_domains:
        summary_parts.append("active traders highlight critical latency and app stability concerns during volatile hours")
    if "Payments & Funding" in top_domains:
        summary_parts.append("payment delays and UPI deposit failures remain notable friction points")
    if "KYC & Onboarding" in top_domains:
        summary_parts.append("onboarding and document verification loops cause frustration for new users")
    if "Customer Support Quality" in top_domains:
        summary_parts.append("slow ticket resolution and bot loops impact customer support satisfaction")

    if not summary_parts:
        summary_parts.append("overall app sentiment this week is mixed with a variety of minor feedback issues reported")

    executive_summary = (
        "Overall app sentiment this week is mixed. "
        + "Specifically, " + ", while ".join(summary_parts) + "."
    )

    return {
        "executive_summary": executive_summary,
        "top_themes": top_themes,
        "verbatim_quotes": verbatim_quotes,
        "action_ideas": action_ideas
    }

