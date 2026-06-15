"""
docs_writer.py — Creates and formats the Groww Review Analyser Google Doc.

Document title:  Groww Review Analyser — {pulse.timeline}
Sections:
  1. Header metadata (timeline, total reviews)
  2. Top 3 Themes with Insights
  3. Verbatim Quotes
  4. Strategic Action Ideas

Uses Google Docs API batchUpdate for rich formatting (headings, bold, bullets).
Prepends the report to an existing Google Document.
Returns the public shareable URL of the document.
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

    title = f"Groww Review Analyser — {pulse.timeline}"

    # Use the existing document requested by the user
    doc_id = "1Ik2W3v6cJxG1PdFEO1jXcCra8U-sSRujlcF1DUq_Hew"
    logger.info("Updating existing Google Doc: %s (id=%s)", title, doc_id)

    # Step 2: Build the document content as plain text first (insert in order)
    # We add a page break \x0C at the end to separate from older reports.
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
    We insert text as a single block first, then apply formatting based on text offsets.
    """
    lines: list[tuple[str, str]] = []  # (text, style_hint)

    # Header / Meta
    lines.append(("\n", "normal"))
    lines.append((f"Report generated automatically by LIP5 · Timeline: {pulse.timeline} · {pulse.total_reviews_analyzed} reviews analysed\n", "meta"))
    lines.append(("\n", "normal"))

    # Executive Summary Section
    lines.append(("📝 Executive Summary\n", "heading2"))
    lines.append((f"{pulse.executive_summary}\n\n", "callout"))

    # Quantitative Metrics Section
    lines.append(("📊 Quantitative Metrics\n", "heading2"))
    
    # Calculate sentiment percentages
    total = max(pulse.total_reviews_analyzed, 1)
    pos_count = pulse.sentiment_breakdown.get("positive", 0)
    neu_count = pulse.sentiment_breakdown.get("neutral", 0)
    neg_count = pulse.sentiment_breakdown.get("negative", 0)
    pos_pct = (pos_count / total) * 100
    neu_pct = (neu_count / total) * 100
    neg_pct = (neg_count / total) * 100

    lines.append(("Sentiment Breakdown:\n", "bold"))
    lines.append((f"  • Positive (4-5★): {pos_pct:.1f}% ({pos_count} reviews)\n", "bullet"))
    lines.append((f"  • Neutral (3★):   {neu_pct:.1f}% ({neu_count} reviews)\n", "bullet"))
    lines.append((f"  • Negative (1-2★): {neg_pct:.1f}% ({neg_count} reviews)\n\n", "bullet"))

    lines.append(("\n", "normal"))

    # Top Themes Section
    lines.append(("📈 Top Themes & Deep Insights\n", "heading2"))
    for theme in pulse.top_themes:
        lines.append((f"{theme.domain}\n", "heading3"))
        lines.append((f"{theme.summary}\n\n", "normal_large"))

    # Verbatim Quotes Section
    lines.append(("💬 Illustrative Verbatim Quotes\n", "heading2"))
    for quote in pulse.verbatim_quotes:
        lines.append((f"★{'★' * quote.rating}{'☆' * (5 - quote.rating)}  [{quote.domain}]\n", "quote_header"))
        lines.append((f'"{quote.quote}"\n\n', "quote_body"))

    # Strategic Actions Section
    lines.append(("🚀 Strategic Action Ideas\n", "heading2"))
    for idea in pulse.action_ideas:
        lines.append((f"• [{idea.domain}] {idea.action}\n", "action_bullet"))

    # Add a page break and an extra newline at the end to cleanly separate from older reports
    lines.append(("\x0C\n", "normal"))

    full_text = "".join(line for line, _ in lines)

    requests: list[dict[str, Any]] = []

    # Insert text at index 1 (after the document title which occupies index 0)
    requests.append({
        "insertText": {
            "location": {"index": 1},
            "text": full_text,
        }
    })

    # Apply formatting
    idx = 1
    for text, style in lines:
        end = idx + len(text)

        if style == "heading2":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {
                        "namedStyleType": "HEADING_2",
                        "spaceAbove": {"magnitude": 18, "unit": "PT"},
                        "spaceBelow": {"magnitude": 6, "unit": "PT"},
                    },
                    "fields": "namedStyleType,spaceAbove,spaceBelow",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "foregroundColor": {"color": {"rgbColor": {"red": 0.1, "green": 0.1, "blue": 0.1}}},
                        "bold": True,
                        "fontSize": {"magnitude": 14, "unit": "PT"},
                    },
                    "fields": "foregroundColor,bold,fontSize",
                }
            })
        elif style == "heading3":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {
                        "namedStyleType": "HEADING_3",
                        "spaceAbove": {"magnitude": 14, "unit": "PT"},
                        "spaceBelow": {"magnitude": 6, "unit": "PT"},
                    },
                    "fields": "namedStyleType,spaceAbove,spaceBelow",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "foregroundColor": {"color": {"rgbColor": {"red": 0.2, "green": 0.2, "blue": 0.2}}},
                        "bold": True,
                        "fontSize": {"magnitude": 12, "unit": "PT"},
                    },
                    "fields": "foregroundColor,bold,fontSize",
                }
            })
        elif style == "bold":
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {"bold": True, "fontSize": {"magnitude": 11, "unit": "PT"}},
                    "fields": "bold,fontSize",
                }
            })
        elif style == "italic":
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "italic": True,
                        "foregroundColor": {"color": {"rgbColor": {"red": 0.3, "green": 0.3, "blue": 0.3}}},
                        "fontSize": {"magnitude": 11, "unit": "PT"},
                    },
                    "fields": "italic,foregroundColor,fontSize",
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
        elif style == "callout":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {
                        "indentStart": {"magnitude": 18, "unit": "PT"},
                        "spaceBelow": {"magnitude": 14, "unit": "PT"},
                    },
                    "fields": "indentStart,spaceBelow",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "foregroundColor": {"color": {"rgbColor": {"red": 0.2, "green": 0.25, "blue": 0.35}}},
                        "italic": True,
                        "fontSize": {"magnitude": 12, "unit": "PT"},
                    },
                    "fields": "foregroundColor,italic,fontSize",
                }
            })
        elif style == "bullet" or style == "action_bullet":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {
                        "indentStart": {"magnitude": 24, "unit": "PT"},
                        "spaceBelow": {"magnitude": 8 if style == "action_bullet" else 4, "unit": "PT"},
                    },
                    "fields": "indentStart,spaceBelow",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "fontSize": {"magnitude": 11, "unit": "PT"},
                        "foregroundColor": {"color": {"rgbColor": {"red": 0.1, "green": 0.1, "blue": 0.1}}},
                    },
                    "fields": "fontSize,foregroundColor",
                }
            })
        elif style == "quote_header":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {
                        "indentStart": {"magnitude": 18, "unit": "PT"},
                        "spaceAbove": {"magnitude": 8, "unit": "PT"},
                    },
                    "fields": "indentStart,spaceAbove",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {"bold": True, "fontSize": {"magnitude": 11, "unit": "PT"}, "foregroundColor": {"color": {"rgbColor": {"red": 0.1, "green": 0.1, "blue": 0.1}}}},
                    "fields": "bold,fontSize,foregroundColor",
                }
            })
        elif style == "quote_body":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {
                        "indentStart": {"magnitude": 18, "unit": "PT"},
                        "spaceBelow": {"magnitude": 12, "unit": "PT"},
                    },
                    "fields": "indentStart,spaceBelow",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "italic": True,
                        "fontSize": {"magnitude": 11, "unit": "PT"},
                        "foregroundColor": {"color": {"rgbColor": {"red": 0.3, "green": 0.3, "blue": 0.3}}},
                    },
                    "fields": "italic,fontSize,foregroundColor",
                }
            })
        elif style == "normal" or style == "normal_large":
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "fontSize": {"magnitude": 12 if style == "normal_large" else 11, "unit": "PT"},
                        "foregroundColor": {"color": {"rgbColor": {"red": 0.1, "green": 0.1, "blue": 0.1}}},
                    },
                    "fields": "fontSize,foregroundColor",
                }
            })

        idx = end

    return requests
