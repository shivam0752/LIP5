# Implementation Plan - Groww App Review Pulse Generator

This document outlines the phased strategy to build the Groww App Store & Play Store review aggregator, classifier, pulse note generator, and email automation tool.

## User Review Required

> [!IMPORTANT]
> **Email Delivery Mechanism**: We suggest using SMTP with an App Password (for Gmail or Outlook) as the default for ease of setup. If OAuth 2.0 via Google Cloud Console is strictly required, please let us know, as it will require manual setup steps from your side.
> 
> **Data Scope**: We will fetch Google Play reviews using the `google-play-scraper` package and App Store reviews using Apple's RSS XML feed (or a similar public feed parser). Both are free and require no developer keys or logins.

---

## Open Questions

> [!WARNING]
> **Review Filtering**: Do you have a specific date window check, or should we dynamically look back exactly 60/90 days from the current date? We recommend exactly 10 weeks (70 days) lookback.
> 
> **Mock Reviews vs Real Scraped Reviews**: The scraper can sometimes be throttled or return fewer historical records depending on Apple RSS feed limitations (RSS feeds are capped at 500 records). Should we include a mock/offline mode with pre-saved/synthetic review data if public scraping is blocked or limited in this environment? We recommend yes, a hybrid mode.

---

## Proposed Changes

### 1. Project Scaffolding
Set up the python environment, dependencies, and configuration.

#### [NEW] [requirements.txt](file:///d:/antigravity/projects/LIP5/requirements.txt)
Define core dependencies: `google-play-scraper`, `pandas`, `streamlit`, `google-genai` (for Gemini API), `python-dotenv`.

#### [NEW] [.env.example](file:///d:/antigravity/projects/LIP5/.env.example)
Define placeholder environment variables: `GEMINI_API_KEY`, `SMTP_SERVER`, `SMTP_PORT`, `SENDER_EMAIL`, `RECEIVER_EMAIL`, `SMTP_PASSWORD` / `APP_PASSWORD`.

---

### Phase 1: Review Scraper & Ingestion (Data Import)
Implement scrapers that collect raw reviews without credentials and output a standardized CSV without PII.

#### [NEW] [scraper.py](file:///d:/antigravity/projects/LIP5/src/scraper.py)
- Google Play Store scraper using `google-play-scraper` for `com.nextbillion.groww`.
- Apple App Store review fetcher via RSS feed parser.
- Deduplication and schema standardization: `rating`, `title`, `review_text`, `date`, `platform`.
- Clean PII: remove usernames, replace specific account/phone patterns with generic tags, output to `data/reviews_raw.csv`.

---

### Phase 2: Theme Classification (Theme Grouping)
Classify imported reviews into exactly 5 pre-seeded themes.

#### [NEW] [classifier.py](file:///d:/antigravity/projects/LIP5/src/classifier.py)
- Group reviews into:
  1. Onboarding & KYC
  2. Payments & Deposits
  3. Portfolio & Statements
  4. Withdrawals & Redemptions
  5. App Stability & UX
- Grouping will use a hybrid technique: rule-based keyword matching first, followed by Gemini 2.5 Flash classification for ambiguous text.
- Save output with classification mapping to `data/reviews_classified.csv`.

---

### Phase 3: Weekly Pulse Note Generator (Gemini 2.5 Flash)
Generate the weekly pulse note based on the categorized data.

#### [NEW] [generator.py](file:///d:/antigravity/projects/LIP5/src/generator.py)
- Prompt Gemini 2.5 Flash with categorized counts, representative quotes, and a strict constraint to remain under 250 words and format as clean Markdown.
- Output contains: Top 3 themes, 3 user quotes, and 3 actionable ideas.
- Save to `data/weekly_pulse_note.md`.

---

### Phase 4: Email Automation (SMTP Draft / API)
Create draft email.

#### [NEW] [mailer.py](file:///d:/antigravity/projects/LIP5/src/mailer.py)
- Script that formats the email subject and body.
- Uses `smtplib` and `email` packages to connect via secure SMTP and send the email draft to the user's alias or self-address, or saves a local SMTP message file (`draft.eml`) as a fallback if mail credentials are not provided.

---

### Phase 5: Streamlit Web UI
Build a user-friendly frontend to control the entire workflow.

#### [NEW] [app.py](file:///d:/antigravity/projects/LIP5/app.py)
- Streamlit application displaying status controls.
- UI elements:
  - Run / Refresh reviews scraper.
  - Review categorization dashboard (charts showing volume per theme).
  - Weekly Pulse Note viewer (rendered markdown).
  - Draft Email preview and "Create Email Draft" trigger button.

---

## Verification Plan

### Automated Tests
- Run validation scripts for file existence, column structures, and PII presence checks.

### Manual Verification
1. Run Streamlit locally (`streamlit run app.py`).
2. Trigger review scraper and verify output CSV creation.
3. Review the generated markdown pulse note against word counts and formatting.
4. Verify received draft email in the configured inbox.
