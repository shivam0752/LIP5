"""
docs_writer.py — Creates and formats the weekly Groww App Pulse Google Doc.

Document title:  Groww Weekly App Pulse — Week Ending DD/MM/YYYY
Sections:
  1. Header metadata (week, total reviews)
  2. Top 3 Themes
  3. Verbatim Quotes
  4. Strategic Action Ideas

Uses Google Docs API batchUpdate for rich formatting (headings, bold, bullets).
Returns the public shareable URL of the created document.
"""

from __future__ import annotations

import logging
from typing import Any

from googleapiclient.discovery import build

from app.api.schemas import PulseDetail
from app.workspace.google_auth import build_credentials

logger = logging.getLogger(__name__)

# Domain → hex color for visual differentiation
DOMAIN_COLORS: dict[str, dict[str, float]] = {
    "Order Execution & Latency":  {"red": 0.8,  "green": 0.2,  "blue": 0.2},
    "Payments & Funding":         {"red": 0.9,  "green": 0.6,  "blue": 0.1},
    "KYC & Onboarding":           {"red": 0.2,  "green": 0.6,  "blue": 0.9},
    "Customer Support Quality":   {"red": 0.6,  "green": 0.3,  "blue": 0.8},
    "App Stability & UI":         {"red": 0.2,  "green": 0.75, "blue": 0.4},
    "Other":                      {"red": 0.5,  "green": 0.5,  "blue": 0.5},
}


def write_pulse_doc(pulse: PulseDetail) -> str:
    """
    Create a formatted Google Doc for the pulse and return its URL.

    Args:
        pulse: validated PulseDetail with all analysis fields populated

    Returns:
        https://docs.google.com/document/d/<doc_id>/edit shareable URL
    """
    creds = build_credentials()
    docs_service = build("docs", "v1", credentials=creds)

    title = f"Groww Weekly App Pulse — Week Ending {pulse.week_ending}"

    # Step 1: Create empty document
    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id: str = doc["documentId"]
    logger.info("Created Google Doc: %s (id=%s)", title, doc_id)

    # Step 2: Build the document content as plain text first (insert in order)
    requests = _build_insert_requests(pulse, title)

    # Step 3: Apply formatting
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    logger.info("Google Doc available at: %s", url)
    return url


def _build_insert_requests(pulse: PulseDetail, title: str) -> list[dict[str, Any]]:
    """
    Build the ordered list of Docs API requests to populate and format the document.
    We insert text in reverse order (from end to start) so index positions remain stable.
    """
    # Build the full text layout first so we can calculate character positions
    lines: list[tuple[str, str]] = []  # (text, style_hint)

    lines.append((f"\n", "normal"))
    lines.append((f"Report generated automatically by LIP5 · {pulse.total_reviews_analyzed} reviews analysed\n", "meta"))
    lines.append(("\n", "normal"))

    lines.append(("📊 Top 3 Themes\n", "heading2"))
    for theme in pulse.top_themes:
        lines.append((f"{theme.domain}\n", "heading3"))
        lines.append((f"{theme.summary}\n\n", "normal"))

    lines.append(("💬 Verbatim Quotes\n", "heading2"))
    for quote in pulse.verbatim_quotes:
        lines.append((f"★{'★' * quote.rating}{'☆' * (5 - quote.rating)}  [{quote.domain}]\n", "bold"))
        lines.append((f'"{quote.quote}"\n\n', "italic"))

    lines.append(("🚀 Strategic Action Ideas\n", "heading2"))
    for idea in pulse.action_ideas:
        lines.append((f"• [{idea.domain}] {idea.action}\n", "normal"))

    # We insert everything as one block, then apply styles with updateTextStyle
    full_text = "".join(line for line, _ in lines)

    requests: list[dict[str, Any]] = []

    # Insert text at index 1 (after the document title which occupies index 0)
    requests.append({
        "insertText": {
            "location": {"index": 1},
            "text": full_text,
        }
    })

    # Apply paragraph styles (heading2, heading3) by recalculating positions
    idx = 1
    for text, style in lines:
        end = idx + len(text)

        if style == "heading2":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {"namedStyleType": "HEADING_2"},
                    "fields": "namedStyleType",
                }
            })
        elif style == "heading3":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {"namedStyleType": "HEADING_3"},
                    "fields": "namedStyleType",
                }
            })
        elif style == "bold":
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {"bold": True},
                    "fields": "bold",
                }
            })
        elif style == "italic":
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {"italic": True},
                    "fields": "italic",
                }
            })
        elif style == "meta":
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "foregroundColor": {"color": {"rgbColor": {"red": 0.4, "green": 0.4, "blue": 0.4}}},
                        "fontSize": {"magnitude": 10, "unit": "PT"},
                        "italic": True,
                    },
                    "fields": "foregroundColor,fontSize,italic",
                }
            })

        idx = end

    return requests
