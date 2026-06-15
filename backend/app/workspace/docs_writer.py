"""
docs_writer.py — Writes the Groww Review Analyser report into an existing Google Doc.

Workflow per run:
  1. Read current doc to find its end index
  2. Delete all existing content (full clear)
  3. Insert fresh report text in one block
  4. Apply clean, consistent formatting

Sections:
  1. Title + metadata line
  2. Executive Summary
  3. Sentiment Breakdown (bullet list)
  4. Top Themes & Insights
  5. Verbatim Quotes
  6. Strategic Action Ideas

Returns the public shareable URL of the document.
"""

from __future__ import annotations

import logging
from typing import Any

from googleapiclient.discovery import build

from app.api.schemas import PulseDetail
from app.workspace.google_auth import build_credentials

logger = logging.getLogger(__name__)

# Fixed Google Doc ID supplied by the user
_DOC_ID = "1Ik2W3v6cJxG1PdFEO1jXcCra8U-sSRujlcF1DUq_Hew"


def write_pulse_doc(pulse: PulseDetail) -> str:
    """
    Clear the existing Google Doc and write a fresh formatted report.

    Returns:
        https://docs.google.com/document/d/<doc_id>/edit shareable URL
    """
    creds = build_credentials()
    docs = build("docs", "v1", credentials=creds)

    logger.info("Writing Review Analyser report to doc %s", _DOC_ID)

    # ── Step 1: Find current doc length ──────────────────────────────────────
    doc = docs.documents().get(documentId=_DOC_ID).execute()
    body_content = doc.get("body", {}).get("content", [])
    # Last structural element gives us the end index
    end_index = body_content[-1]["endIndex"] if body_content else 2

    # ── Step 2: Clear all existing content ───────────────────────────────────
    clear_requests: list[dict[str, Any]] = []
    if end_index > 2:
        clear_requests.append({
            "deleteContentRange": {
                "range": {
                    "startIndex": 1,
                    "endIndex": end_index - 1,
                }
            }
        })
        docs.documents().batchUpdate(
            documentId=_DOC_ID,
            body={"requests": clear_requests},
        ).execute()
        logger.info("Cleared existing doc content (was %d chars)", end_index)

    # ── Step 3: Build content lines ───────────────────────────────────────────
    title = f"Groww Review Analyser — {pulse.timeline}"
    requests = _build_requests(pulse, title)

    # ── Step 4: Apply all inserts + formatting ────────────────────────────────
    docs.documents().batchUpdate(
        documentId=_DOC_ID,
        body={"requests": requests},
    ).execute()

    url = f"https://docs.google.com/document/d/{_DOC_ID}/edit"
    logger.info("Report written: %s", url)
    return url


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rgb(r: float, g: float, b: float) -> dict:
    return {"color": {"rgbColor": {"red": r, "green": g, "blue": b}}}


def _build_requests(pulse: PulseDetail, title: str) -> list[dict[str, Any]]:
    """
    Build the full list of Docs API batchUpdate requests:
      - One insertText for all content
      - Followed by updateParagraphStyle / updateTextStyle per section
    """
    # Each entry: (text, style_key)
    lines: list[tuple[str, str]] = []

    # ── Title ────────────────────────────────────────────────────────────────
    lines.append((f"{title}\n", "title"))

    # ── Meta line ────────────────────────────────────────────────────────────
    lines.append((
        f"Timeline: {pulse.timeline}  ·  {pulse.total_reviews_analyzed} reviews analysed\n\n",
        "meta"
    ))

    # ── Executive Summary ─────────────────────────────────────────────────────
    lines.append(("Executive Summary\n", "h2"))
    lines.append((f"{pulse.executive_summary}\n\n", "body"))

    # ── Sentiment Breakdown ───────────────────────────────────────────────────
    total = max(pulse.total_reviews_analyzed, 1)
    pos   = pulse.sentiment_breakdown.get("positive", 0)
    neu   = pulse.sentiment_breakdown.get("neutral",  0)
    neg   = pulse.sentiment_breakdown.get("negative", 0)

    lines.append(("Sentiment Breakdown\n", "h2"))
    lines.append((f"Positive (4–5 ★)   {pos} reviews  ({pos/total*100:.1f}%)\n", "bullet"))
    lines.append((f"Neutral  (3 ★)      {neu} reviews  ({neu/total*100:.1f}%)\n", "bullet"))
    lines.append((f"Negative (1–2 ★)   {neg} reviews  ({neg/total*100:.1f}%)\n\n", "bullet"))

    # ── Top Themes ────────────────────────────────────────────────────────────
    lines.append(("Top Themes & Insights\n", "h2"))
    for i, theme in enumerate(pulse.top_themes, 1):
        lines.append((f"{i}. {theme.domain}\n", "h3"))
        lines.append((f"{theme.summary}\n\n", "body"))

    # ── Verbatim Quotes ───────────────────────────────────────────────────────
    lines.append(("Verbatim Quotes\n", "h2"))
    for q in pulse.verbatim_quotes:
        stars = "★" * q.rating + "☆" * (5 - q.rating)
        lines.append((f"{stars}  ·  {q.domain}\n", "quote_label"))
        lines.append((f'"{q.quote}"\n\n', "quote_body"))

    # ── Action Ideas ──────────────────────────────────────────────────────────
    lines.append(("Strategic Action Ideas\n", "h2"))
    for idea in pulse.action_ideas:
        lines.append((f"[{idea.domain}]  {idea.action}\n", "bullet"))

    # ── Assemble full text ────────────────────────────────────────────────────
    full_text = "".join(t for t, _ in lines)
    requests: list[dict[str, Any]] = []

    # Single insert at position 1
    requests.append({
        "insertText": {
            "location": {"index": 1},
            "text": full_text,
        }
    })

    # ── Apply formatting pass ─────────────────────────────────────────────────
    idx = 1
    for text, style in lines:
        end = idx + len(text)

        if style == "title":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {
                        "namedStyleType": "TITLE",
                        "spaceBelow": {"magnitude": 4, "unit": "PT"},
                    },
                    "fields": "namedStyleType,spaceBelow",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "bold": True,
                        "fontSize": {"magnitude": 20, "unit": "PT"},
                        "foregroundColor": _rgb(0.07, 0.07, 0.07),
                    },
                    "fields": "bold,fontSize,foregroundColor",
                }
            })

        elif style == "meta":
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "italic": True,
                        "fontSize": {"magnitude": 10, "unit": "PT"},
                        "foregroundColor": _rgb(0.45, 0.45, 0.45),
                    },
                    "fields": "italic,fontSize,foregroundColor",
                }
            })

        elif style == "h2":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {
                        "namedStyleType": "HEADING_2",
                        "spaceAbove": {"magnitude": 16, "unit": "PT"},
                        "spaceBelow": {"magnitude": 4, "unit": "PT"},
                    },
                    "fields": "namedStyleType,spaceAbove,spaceBelow",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "bold": True,
                        "fontSize": {"magnitude": 13, "unit": "PT"},
                        "foregroundColor": _rgb(0.1, 0.1, 0.1),
                    },
                    "fields": "bold,fontSize,foregroundColor",
                }
            })

        elif style == "h3":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {
                        "namedStyleType": "HEADING_3",
                        "spaceAbove": {"magnitude": 10, "unit": "PT"},
                        "spaceBelow": {"magnitude": 2, "unit": "PT"},
                    },
                    "fields": "namedStyleType,spaceAbove,spaceBelow",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "bold": True,
                        "fontSize": {"magnitude": 11, "unit": "PT"},
                        "foregroundColor": _rgb(0.15, 0.15, 0.15),
                    },
                    "fields": "bold,fontSize,foregroundColor",
                }
            })

        elif style == "body":
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "fontSize": {"magnitude": 11, "unit": "PT"},
                        "foregroundColor": _rgb(0.15, 0.15, 0.15),
                        "bold": False,
                        "italic": False,
                    },
                    "fields": "fontSize,foregroundColor,bold,italic",
                }
            })

        elif style == "bullet":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {
                        "indentStart": {"magnitude": 18, "unit": "PT"},
                        "spaceBelow": {"magnitude": 3, "unit": "PT"},
                    },
                    "fields": "indentStart,spaceBelow",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "fontSize": {"magnitude": 11, "unit": "PT"},
                        "foregroundColor": _rgb(0.15, 0.15, 0.15),
                    },
                    "fields": "fontSize,foregroundColor",
                }
            })

        elif style == "quote_label":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {
                        "spaceAbove": {"magnitude": 8, "unit": "PT"},
                        "spaceBelow": {"magnitude": 2, "unit": "PT"},
                    },
                    "fields": "spaceAbove,spaceBelow",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "textStyle": {
                        "bold": True,
                        "fontSize": {"magnitude": 10, "unit": "PT"},
                        "foregroundColor": _rgb(0.35, 0.35, 0.35),
                    },
                    "fields": "bold,fontSize,foregroundColor",
                }
            })

        elif style == "quote_body":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {
                        "indentStart": {"magnitude": 18, "unit": "PT"},
                        "spaceBelow": {"magnitude": 6, "unit": "PT"},
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
                        "foregroundColor": _rgb(0.25, 0.25, 0.25),
                    },
                    "fields": "italic,fontSize,foregroundColor",
                }
            })

        idx = end

    return requests
