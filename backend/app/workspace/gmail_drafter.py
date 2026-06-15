"""
gmail_drafter.py — Stages a Gmail draft with the weekly pulse content + Doc link.

Draft subject:  [Weekly App Pulse] Groww Store Review Insights - Week Ending DD/MM/YYYY
Draft body:     Plain-text executive pulse + Google Doc link

Uses Gmail API (gmail.compose scope) — no emails are sent, only drafted.
Returns the draft ID.
"""

from __future__ import annotations

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from googleapiclient.discovery import build

from app.api.schemas import PulseDetail
from app.workspace.google_auth import build_credentials

logger = logging.getLogger(__name__)


def stage_draft(pulse: PulseDetail, doc_url: Optional[str] = None) -> str:
    """
    Create a Gmail draft with the pulse summary and return the draft ID.

    Args:
        pulse:   validated PulseDetail
        doc_url: Google Doc URL to embed in the email body (optional)

    Returns:
        Gmail draft ID string
    """
    creds = build_credentials()
    gmail_service = build("gmail", "v1", credentials=creds)

    subject = (
        f"[Weekly App Pulse] Groww Store Review Insights - Week Ending {pulse.week_ending}"
    )
    body = _build_email_body(pulse, doc_url)

    # Fetch the authenticated user's real email address
    profile = gmail_service.users().getProfile(userId="me").execute()
    user_email: str = profile.get("emailAddress", "")

    # Build MIME message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user_email
    msg["To"] = user_email  # Draft addressed to self — edit before sending

    plain_part = MIMEText(body, "plain", "utf-8")
    html_part = MIMEText(_build_html_body(pulse, doc_url), "html", "utf-8")
    msg.attach(plain_part)
    msg.attach(html_part)

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    draft = (
        gmail_service.users()
        .drafts()
        .create(
            userId="me",
            body={"message": {"raw": raw_message}},
        )
        .execute()
    )

    draft_id: str = draft["id"]
    logger.info("Gmail draft staged: id=%s, subject=%s", draft_id, subject)
    return draft_id


def _build_email_body(pulse: PulseDetail, doc_url: Optional[str]) -> str:
    """Build plain-text email body."""
    lines = [
        f"GROWW WEEKLY APP PULSE — Week Ending {pulse.week_ending}",
        f"Total Reviews Analysed: {pulse.total_reviews_analyzed}",
        "=" * 60,
        "",
        "📊 TOP 3 THEMES",
        "-" * 40,
    ]

    for i, theme in enumerate(pulse.top_themes, 1):
        lines.append(f"{i}. {theme.domain}")
        lines.append(f"   {theme.summary}")
        lines.append("")

    lines += [
        "💬 VERBATIM QUOTES",
        "-" * 40,
    ]
    for quote in pulse.verbatim_quotes:
        stars = "★" * quote.rating + "☆" * (5 - quote.rating)
        lines.append(f'"{quote.quote}"')
        lines.append(f"   — {stars} · {quote.domain}")
        lines.append("")

    lines += [
        "🚀 STRATEGIC ACTION IDEAS",
        "-" * 40,
    ]
    for idea in pulse.action_ideas:
        lines.append(f"• [{idea.domain}] {idea.action}")

    lines += [""]

    if doc_url:
        lines += [
            "=" * 60,
            f"📄 Full Report (Google Docs): {doc_url}",
        ]

    lines += [
        "",
        "—",
        "This report was generated automatically by LIP5 (Automated App Store Pulse).",
        "Do not reply to this draft — edit and send to your intended recipients.",
    ]

    return "\n".join(lines)


def _build_html_body(pulse: PulseDetail, doc_url: Optional[str]) -> str:
    """Build HTML email body with basic styling."""
    domain_colors = {
        "Order Execution & Latency": "#e53e3e",
        "Payments & Funding": "#dd6b20",
        "KYC & Onboarding": "#3182ce",
        "Customer Support Quality": "#805ad5",
        "App Stability & UI": "#38a169",
        "Other": "#718096",
    }

    def domain_badge(domain: str) -> str:
        color = domain_colors.get(domain, "#718096")
        return (
            f'<span style="background:{color};color:white;padding:2px 8px;'
            f'border-radius:12px;font-size:12px;font-weight:600;">{domain}</span>'
        )

    themes_html = ""
    for theme in pulse.top_themes:
        themes_html += (
            f"<li style='margin-bottom:12px;'>"
            f"{domain_badge(theme.domain)}"
            f"<p style='margin:6px 0 0;color:#2d3748;'>{theme.summary}</p>"
            f"</li>"
        )

    quotes_html = ""
    for quote in pulse.verbatim_quotes:
        stars = "★" * quote.rating + "☆" * (5 - quote.rating)
        quotes_html += (
            f"<li style='margin-bottom:12px;'>"
            f"<blockquote style='border-left:3px solid #e2e8f0;margin:0;padding:4px 12px;"
            f"color:#4a5568;font-style:italic;'>\"{quote.quote}\"</blockquote>"
            f"<small style='color:#718096;'>{stars} · {domain_badge(quote.domain)}</small>"
            f"</li>"
        )

    actions_html = ""
    for idea in pulse.action_ideas:
        actions_html += (
            f"<li style='margin-bottom:10px;'>"
            f"{domain_badge(idea.domain)} "
            f"<span style='color:#2d3748;'>{idea.action}</span>"
            f"</li>"
        )

    doc_section = ""
    if doc_url:
        doc_section = (
            f'<p style="margin-top:24px;">'
            f'📄 <strong>Full Report:</strong> '
            f'<a href="{doc_url}" style="color:#3182ce;">View in Google Docs</a>'
            f"</p>"
        )

    return f"""<!DOCTYPE html>
<html>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#1a202c;">
  <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:24px;border-radius:12px;margin-bottom:24px;">
    <h1 style="color:white;margin:0;font-size:22px;">📱 Groww Weekly App Pulse</h1>
    <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;">
      Week Ending {pulse.week_ending} &nbsp;·&nbsp; {pulse.total_reviews_analyzed} reviews analysed
    </p>
  </div>

  <h2 style="color:#2d3748;font-size:18px;">📊 Top 3 Themes</h2>
  <ul style="padding-left:0;list-style:none;">{themes_html}</ul>

  <h2 style="color:#2d3748;font-size:18px;">💬 Verbatim Quotes</h2>
  <ul style="padding-left:0;list-style:none;">{quotes_html}</ul>

  <h2 style="color:#2d3748;font-size:18px;">🚀 Strategic Action Ideas</h2>
  <ul style="padding-left:0;list-style:none;">{actions_html}</ul>

  {doc_section}

  <hr style="border:none;border-top:1px solid #e2e8f0;margin-top:32px;">
  <p style="color:#a0aec0;font-size:12px;">
    Generated automatically by LIP5 — Automated App Store Pulse System.<br>
    Edit this draft before sending to your intended recipients.
  </p>
</body>
</html>"""
