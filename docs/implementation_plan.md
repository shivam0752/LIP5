# LIP5: Automated App Store Pulse & Governance Workflow
## Implementation Plan

> **Product:** Groww | **Stack:** FastAPI · React/Vite · Gemini API · Google Docs/Gmail API · Railway

Build a full-stack internal tool that ingests app store reviews weekly, classifies them with Gemini into 5 fintech domains, generates a Google Doc executive pulse, and stages a Gmail draft — with a React dashboard for live monitoring and manual triggers.

---

## Technology Stack

| Concern | Choice | Rationale |
|---|---|---|
| Backend | **Python + FastAPI** | Async-native, `uvicorn` plays well with Railway |
| Frontend | **React + Vite** | Lightweight SPA; ideal for an ops dashboard |
| LLM | **Gemini 1.5 Flash** | Stays within GCP ecosystem; fast & cost-efficient |
| Google Auth | **OAuth 2.0** (`google-auth-oauthlib`) | Required for personal Docs & Gmail access |
| Scheduler | **APScheduler** (AsyncIOScheduler) | Embedded in FastAPI; no extra infra |
| Storage | **JSON flat files** | Zero-config; Supabase migration path available |
| Reviews | **`google-play-scraper`** + iOS simulation | Public data only; no auth required |
| Tests | **pytest** + **pytest-asyncio** | Unit coverage on all core pipeline functions |
| Deployment | **Railway** (2 services: API + static frontend) | Simplest monorepo-to-cloud path |

---

## Repository Layout

```
LIP5/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry + lifespan
│   │   ├── scheduler.py         # APScheduler weekly cron
│   │   ├── config.py            # pydantic-settings env config
│   │   ├── ingestion/
│   │   │   ├── play_store.py    # google-play-scraper wrapper
│   │   │   └── sanitizer.py    # PII regex scrubber
│   │   ├── analysis/
│   │   │   ├── classifier.py   # Gemini → 5-domain classification
│   │   │   └── summarizer.py   # Gemini → ≤250-word pulse
│   │   ├── workspace/
│   │   │   ├── google_auth.py  # OAuth2 + token.json cache
│   │   │   ├── docs_writer.py  # Google Docs API
│   │   │   └── gmail_drafter.py # Gmail draft API
│   │   ├── storage/store.py    # flat-file helpers + log writer
│   │   └── api/
│   │       ├── routes.py       # REST endpoints + pipeline orchestrator
│   │       └── schemas.py      # Pydantic models
│   ├── data/reviews/  data/pulses/  data/logs.jsonl
│   ├── tests/
│   ├── requirements.txt · .env.example · Procfile
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx + pages/ + components/
│   └── vite.config.js · package.json · .env.example
│
├── docs/
│   ├── problemstatement.md
│   ├── implementation_plan.md
│   └── sample_reviews.csv
└── README.md
```

---

## Phase 1 — Project Foundation & Backend Scaffold

> **Goal:** Establish the repo skeleton, environment config, FastAPI app, and APScheduler. By the end of this phase, the server starts cleanly with all routes registered and the cron job wired in.

### Deliverables

| File | Purpose |
|---|---|
| [NEW] `backend/requirements.txt` | All Python dependencies pinned |
| [NEW] `backend/.env.example` | Template for all required env vars |
| [NEW] `backend/Procfile` | Railway start command |
| [NEW] `backend/app/config.py` | `pydantic-settings` config with derived path helpers |
| [NEW] `backend/app/main.py` | FastAPI app with CORS, lifespan, router mount |
| [NEW] `backend/app/scheduler.py` | APScheduler cron — every Sunday 00:00 UTC |
| [NEW] `backend/app/storage/store.py` | JSON flat-file helpers + log appender + run-state tracker |
| [NEW] `backend/app/api/schemas.py` | Pydantic request/response models |
| [NEW] `backend/app/api/routes.py` | All REST endpoints (health, pulses, trigger, status, logs) |

### API Endpoints (registered in this phase)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/pulses` | List all historical pulse summaries |
| `GET` | `/api/pulses/{id}` | Get a specific pulse detail |
| `POST` | `/api/trigger` | Manually trigger pipeline for a date range |
| `GET` | `/api/status` | Current pipeline run status |
| `GET` | `/api/logs` | Paginated logs (polled every 5s by frontend) |

### Key Config Variables
```
GEMINI_API_KEY
GOOGLE_CLIENT_SECRETS_FILE   # path to credentials.json
GROWW_PACKAGE_NAME           # com.nextbillion.groww
CORS_ORIGINS                 # comma-separated frontend origins
DATA_DIR                     # defaults to ./data
```

---

## Phase 2 — Data Ingestion Pipeline

> **Goal:** Build the full ingestion pipeline — scraping Play Store reviews, simulating iOS reviews, enforcing PII sanitization, and persisting clean data to the flat-file store.

### Deliverables

| File | Purpose |
|---|---|
| [NEW] `backend/app/ingestion/play_store.py` | Play Store scraper + iOS simulation dataset |
| [NEW] `backend/app/ingestion/sanitizer.py` | PII regex engine (email, phone, UPI, PAN, Aadhaar) |
| [NEW] `docs/sample_reviews.csv` | 25-50 redacted Android + iOS reviews for submission |

### Ingestion Details

**Corpus schema** (every row must conform):
```
{ rating, review_title, review_text, date, platform }
```

**Android** — `google-play-scraper` fetches up to 200 newest reviews, filtered to the `[start_date, end_date]` window.

**iOS** — 25 pre-authored realistic reviews tagged `platform: "iOS"`, randomly spread across the same window. Satisfies the submission's mixed-platform requirement without App Store Connect credentials.

**PII Sanitization rules** (regex-first, then discard if body < 10 chars post-clean):

| Pattern | Example | Action |
|---|---|---|
| Email | `user@domain.com` | → `[REDACTED]` |
| Indian phone | `9876543210` | → `[REDACTED]` |
| UPI ID | `name@okicici` | → `[REDACTED]` |
| PAN card | `ABCDE1234F` | → `[REDACTED]` |
| Aadhaar | `1234 5678 9012` | → `[REDACTED]` |
| Tracker string | 16+ char alphanumeric | → `[REDACTED]` |

---

## Phase 3 — AI Analysis Engine (Gemini)

> **Goal:** Wire the Gemini API to classify every sanitized review into one of 5 fintech domains and generate a ≤250-word structured pulse report with themes, quotes, and action ideas.

### Deliverables

| File | Purpose |
|---|---|
| [NEW] `backend/app/analysis/classifier.py` | Batch Gemini classification → domain tags |
| [NEW] `backend/app/analysis/summarizer.py` | Gemini summarization → pulse JSON |

### Classification Domains

| # | Domain | Example signals |
|---|---|---|
| 1 | **Order Execution & Latency** | Options slippage, delayed limit orders, chart mismatches |
| 2 | **Payments & Funding** | Bank deposits, UPI failures, settlement cycles |
| 3 | **KYC & Onboarding** | Account creation, re-KYC, document verification |
| 4 | **Customer Support Quality** | Agent responsiveness, bot loops, ticket resolution |
| 5 | **App Stability & UI** | Post-update crashes, freezes at market open |

Classifier output per review: `{ id, domain, confidence }`. Batches of 50. Falls back to `"Other"` on Gemini errors.

### Pulse Output Schema (≤ 250 words total)
```json
{
  "top_themes":       [ { "domain", "summary" } × 3 ],
  "verbatim_quotes":  [ { "quote", "domain", "rating" } × 3 ],
  "action_ideas":     [ { "action", "domain" } × 3 ],
  "week_ending":      "DD/MM/YYYY",
  "total_reviews_analyzed": <int>
}
```

---

## Phase 4 — Google Workspace Integration & Frontend Dashboard

> **Goal:** Push the pulse artifact to Google Drive and Gmail, and build the React dashboard for real-time monitoring, manual pipeline triggers, and historical pulse browsing.

### Deliverables

#### Backend — Google Workspace

| File | Purpose |
|---|---|
| [NEW] `backend/app/workspace/google_auth.py` | OAuth2 flow + `token.json` caching + silent refresh |
| [NEW] `backend/app/workspace/docs_writer.py` | Creates & formats the Google Doc pulse report |
| [NEW] `backend/app/workspace/gmail_drafter.py` | Stages Gmail draft with correct subject line |

**Google Doc** — Title: `Groww Weekly App Pulse — Week Ending DD/MM/YYYY`
Sections: Top 3 Themes · Verbatim Quotes · Strategic Action Ideas. Formatted via `batchUpdate`.

**Gmail Draft** — Subject: `[Weekly App Pulse] Groww Store Review Insights - Week Ending DD/MM/YYYY`
Body: plain-text pulse + Google Doc link.

**OAuth Scopes:**
- `https://www.googleapis.com/auth/documents`
- `https://www.googleapis.com/auth/gmail.compose`

> **Railway note:** `token.json` must be generated locally first (run `python -m app.workspace.google_auth`), then mounted as a Railway secret file — the browser OAuth flow cannot run headlessly on Railway.

---

#### Frontend — React + Vite Dashboard

| File | Purpose |
|---|---|
| [NEW] `frontend/src/index.css` | Design system (dark theme, tokens, animations) |
| [NEW] `frontend/src/App.jsx` | Root component with `react-router-dom` routing |
| [NEW] `frontend/src/pages/Dashboard.jsx` | Current week themes, sync status badges, trigger |
| [NEW] `frontend/src/pages/Logs.jsx` | Terminal-style log viewer, polls `/api/logs` every 5s |
| [NEW] `frontend/src/pages/History.jsx` | Past pulses table with Doc links |
| [NEW] `frontend/src/components/TriggerButton.jsx` | Date-range picker + manual run button |
| [NEW] `frontend/src/components/ThemeCard.jsx` | Themed domain card with color-coded accent |
| [NEW] `frontend/src/components/StatusBadge.jsx` | Animated idle / running / success / error badge |

**Dashboard sync status indicators:**

| Stage | Tracked |
|---|---|
| ▶ Play Store Ingestion | ✅ |
| ▶ PII Sanitization | ✅ |
| ▶ Gemini Classification | ✅ |
| ▶ Google Docs Sync | ✅ |
| ▶ Gmail Draft Staged | ✅ |

---

## Phase 5 — Testing, Deployment & Documentation

> **Goal:** Achieve full unit test coverage on core pipeline functions, deploy both services to Railway, and produce the final README with setup instructions for reviewers.

### Deliverables

#### Tests

| File | Coverage |
|---|---|
| [NEW] `backend/tests/test_sanitizer.py` | Regex rules: email, phone, UPI, PAN, Aadhaar stripped |
| [NEW] `backend/tests/test_classifier.py` | Mocked Gemini — domain mapping logic validated |
| [NEW] `backend/tests/test_summarizer.py` | Output word count ≤ 250; required keys present |
| [NEW] `backend/tests/test_routes.py` | FastAPI `TestClient` — all endpoints return correct shapes |

```bash
cd backend
pytest tests/ -v --tb=short
```

#### Railway Deployment

Two services in one Railway project (monorepo):

| Service | Root Dir | Build | Start |
|---|---|---|---|
| `lip5-api` | `backend/` | `pip install -r requirements.txt` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| `lip5-frontend` | `frontend/` | `npm install && npm run build` | *(static — serve `dist/`)* |

#### README Sections
- GCP Console setup (OAuth Client ID/Secret, authorized redirect URIs)
- First-time OAuth flow: `python -m app.workspace.google_auth`
- APScheduler cron configuration & timezone notes
- Railway deployment walkthrough (env vars per service)
- **Theme Legend** — how edge-case reviews are routed to domains
- Sample reviews dataset description

---

## Verification Checklist

| Check | How |
|---|---|
| Server starts cleanly | `uvicorn app.main:app --reload` — no import errors |
| OAuth token saved | `python -m app.workspace.google_auth` → `token.json` created |
| Manual trigger works | `POST /api/trigger` → Doc in Drive + draft in Gmail |
| Reviews sanitized | `data/reviews/<run_id>.json` contains no PII patterns |
| Log polling works | Logs page refreshes every 5s with new entries |
| All tests pass | `pytest tests/ -v` — 0 failures |
| Railway services live | Both services green in Railway dashboard |

---

## Notes

> **iOS reviews:** `google-play-scraper` is Android-only. iOS reviews are simulated with 25 pre-authored realistic entries matching real Groww complaint patterns (`platform: "iOS"`). This satisfies the 25-50 mixed-platform submission requirement.

> **Supabase:** JSON flat files are used for now. Migration to Supabase requires only swapping `backend/app/storage/store.py` for a Supabase client — all callers remain unchanged.
