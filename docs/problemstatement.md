# LIP5 — Problem Statement

## Weekly Review Pulse: Groww App Store & Play Store Analyser

**Product Selected:** Groww (carried forward from LIP4)
**LIP4 Context:** In LIP4, we built a facts-only RAG-based FAQ assistant for Groww users covering Mirae Asset Mutual Fund schemes. LIP5 continues with the same product — now shifting focus from *answering questions* to *listening to users at scale*.

---

## The Problem

Groww's product, support, and leadership teams receive thousands of user reviews across the Google Play Store and Apple App Store every week. These reviews contain real signal: broken flows, confusing UX, unmet expectations — but the volume makes it impossible to read manually. Today, insights stay buried in raw text, and the teams that need them (product, growth, support) operate without a structured, recurring view of what users are actually saying.

**LIP5 solves this by building a free, automated pipeline that:**
- Imports the last 8–12 weeks of public Groww reviews
- Groups them into up to 5 actionable themes
- Generates a weekly one-page pulse note (≤250 words)
- Drafts a ready-to-send email containing the note

---

## Who This Helps

| Audience | Value |
|---|---|
| **Product / Growth Teams** | Know what to fix next, backed by real user language |
| **Support Teams** | Understand recurring pain points; acknowledge them confidently |
| **Leadership** | Quick weekly health pulse — no dashboard login needed |

---

## What Must Be Built

### 1. Data Import
- Collect Groww App Store + Play Store reviews from the last **8–12 weeks**
- Fields: `rating`, `title`, `review_text`, `date`, `platform`
- Source: **Public review exports only** — no scraping behind logins
- Strip all PII before storage (no usernames, reviewer IDs, emails)

### 2. Theme Grouping
- Cluster reviews into **≤5 themes** using keyword matching or LLM-assisted classification
- Suggested initial themes (to be validated against actual review data):

| # | Theme | Example Keywords |
|---|---|---|
| 1 | **Onboarding / KYC** | account open, KYC stuck, verification, documents |
| 2 | **Payments & Deposits** | UPI failed, bank link, deposit, add money |
| 3 | **Portfolio & Statements** | statement, gains, portfolio, P&L, holdings |
| 4 | **Withdrawals & Redemptions** | withdrawal, redeem, stuck, pending, money |
| 5 | **App Stability & UX** | crash, slow, freeze, login, update, UI |

### 3. Weekly One-Page Pulse Note
Generated output must include:
- **Top 3 themes** (ranked by review volume this week)
- **3 real user quotes** (verbatim, anonymised — no names/IDs)
- **3 action ideas** (product or support recommendations)
- Word count ≤250 words
- Format: Markdown (also exportable to PDF/Doc)

### 4. Email Draft
- Compose a draft email containing the weekly note
- Recipient: self / internal alias (e.g., `pulse@yourteam.com`)
- Subject: `Groww Weekly Review Pulse — Week of [DATE]`
- Method: Gmail draft via API (free tier) or SMTP with app password
- No PII in email body or attachments

---

## Key Constraints

| Constraint | Detail |
|---|---|
| **Data source** | Public review exports only (no authenticated scraping) |
| **Theme cap** | Maximum 5 themes |
| **Note length** | ≤250 words, scannable format |
| **PII** | No usernames, emails, reviewer IDs, or account numbers in any artifact |
| **Cost** | Free tier only — no paid APIs required |

---

## Proposed Free-Tier Tech Stack

| Component | Tool / Service | Cost |
|---|---|---|
| Review data | `google-play-scraper` (PyPI) + App Store RSS feed | Free |
| LLM for grouping & note | Google Gemini 2.5 Flash (AI Studio free tier) | Free |
| Email draft | Gmail API (OAuth 2.0, free) or SMTP | Free |
| UI / runner | Streamlit (local) or Python CLI script | Free |
| Output storage | Local filesystem (CSV + MD files) | Free |

---

## Deliverables

| # | Deliverable | Format |
|---|---|---|
| 1 | Working prototype | Streamlit app or CLI — local demo / ≤3-min video |
| 2 | Latest weekly pulse note | `.md` file (PDF/Doc export optional) |
| 3 | Email draft | Screenshot or plain text copy |
| 4 | Reviews CSV used | `reviews_sample.csv` — redacted, no PII |
| 5 | README | Re-run instructions + theme legend |

---

## Workflow Overview

```
[Public App Store / Play Store Reviews]
            │
            ▼
  [Import & Clean Reviews CSV]
  (strip PII, last 8–12 weeks)
            │
            ▼
  [Theme Classifier]
  (≤5 themes via keyword + LLM)
            │
            ▼
  [Weekly Pulse Generator — Gemini]
  (Top 3 themes · 3 quotes · 3 actions · ≤250 words)
            │
            ▼
  [Email Drafter]
  (Gmail API draft → self/alias)
            │
            ▼
  [Output: pulse_note.md + email_draft.txt]
```

---

## Skills Being Tested

| Week | Skill Area | Application in LIP5 |
|---|---|---|
| **W2** | LLMs & Prompting | Summarisation, quote selection, tone control for pulse note |
| **W2** | LLMs & Prompting | Structured output (themes, quotes, actions) from messy review text |
| **W3** | AI Workflow Automations | Import → Group → Generate Note → Draft Email pipeline |

---

## Open Questions / Decisions to Confirm

1. **Review volume**: How many weeks of Groww reviews are available via the public scraper? (Target: 8–12 weeks, ~200–500 reviews)
2. **Theme validation**: Should the 5 themes be fixed upfront or dynamically inferred by the LLM each week?
3. **Email method**: Gmail API (requires OAuth setup) vs. SMTP with app password — which is preferred for simplicity?
4. **Output format**: Is Markdown sufficient for the pulse note, or is a PDF/HTML render needed for the demo?
5. **Scheduling**: One-shot script for now, or should the pipeline be scheduled weekly (e.g., every Monday 9am)?

---

*Prepared for LIP5 | Product: Groww | Continued from LIP4 (Mirae Asset MF FAQ Assistant)*
*Date: June 2026*
