# LIP5 — Automated App Store Pulse & Governance Workflow

> **Stack:** FastAPI · React/Vite · Gemini 2.5 Flash · Google Docs/Gmail API · Railway  
> **Product:** Groww (India's leading investment app)

LIP5 is a full-stack internal tool that automatically ingests Groww app-store reviews every week, classifies them with Gemini into 5 fintech domains, generates a Google Doc executive pulse, and stages a Gmail draft — with a React dashboard for live monitoring and manual pipeline triggers.

---

## Architecture

```
LIP5/
├── backend/      FastAPI + APScheduler + Gemini + Google Workspace APIs
├── frontend/     React + Vite dashboard (dark theme, live log polling)
└── docs/         Implementation plan, sample reviews dataset
```

**Pipeline stages (each tracked live on the dashboard):**

| # | Stage | Tool |
|---|---|---|
| 1 | Play Store Ingestion | `google-play-scraper` + 25 iOS simulation reviews |
| 2 | PII Sanitization | Regex engine (email, phone, UPI, PAN, Aadhaar) |
| 3 | Gemini Classification | Gemini 1.5 Flash → 5 fintech domains |
| 4 | Gemini Summarization | ≤250-word structured pulse JSON |
| 5 | Google Docs Sync | `batchUpdate` formatted report |
| 6 | Gmail Draft Staged | Subject-lined draft in inbox |

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 18+
- A GCP project with **Gemini API** and **Google Workspace APIs** enabled

---

### 1. Clone & Set Up Backend

```bash
git clone https://github.com/your-org/LIP5.git
cd LIP5/backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Copy and fill in the environment file:

```bash
cp .env.example .env
```

| Variable | Value |
|---|---|
| `GEMINI_API_KEY` | From [Google AI Studio](https://aistudio.google.com/) |
| `GOOGLE_CLIENT_SECRETS_FILE` | Path to `credentials.json` (see GCP Setup below) |
| `GOOGLE_CLIENT_SECRETS_JSON` | Raw JSON string content of `credentials.json` (alternative to file) |
| `GOOGLE_TOKEN_JSON` | Raw JSON string content of `token.json` (alternative to file) |
| `GROWW_PACKAGE_NAME` | `com.nextbillion.groww` |
| `CORS_ORIGINS` | `http://localhost:5173` |
| `DATA_DIR` | `./data` (default) |

Start the backend:

```bash
uvicorn app.main:app --reload
# API live at http://localhost:8000
# Docs at  http://localhost:8000/docs
```

---

### 2. Set Up Frontend

```bash
cd LIP5/frontend
npm install

# Copy env
cp .env.example .env.local
# Set VITE_API_URL=http://localhost:8000
```

Start the frontend:

```bash
npm run dev
# Dashboard at http://localhost:5173
```

---

## GCP Console Setup

### Step 1 — Enable APIs

In [Google Cloud Console](https://console.cloud.google.com/):

1. Navigate to **APIs & Services → Library**
2. Enable:
   - **Google Docs API**
   - **Gmail API**
   - **Generative Language API** (for Gemini)

### Step 2 — Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Download the JSON file and save it as `backend/credentials.json`

**Required OAuth Scopes:**
```
https://www.googleapis.com/auth/documents
https://www.googleapis.com/auth/gmail.compose
```

### Step 3 — Authorized Redirect URIs

Add the following to your OAuth client:
```
http://localhost:8080/
```

> **Note:** This is only needed for the local first-time token generation flow.

---

## First-Time OAuth Flow

The Google OAuth browser flow **cannot run headlessly** (e.g., on Railway). You must generate `token.json` locally first, and then configure the `GOOGLE_TOKEN_JSON` environment variable with the file's JSON content (recommended) or mount the file.

```bash
cd backend
python -m app.workspace.google_auth
```

This will:
1. Open a browser window asking you to authorize the app
2. Save the OAuth token to `backend/token.json`

Keep this file safe — **never commit it to Git**. You can copy the contents of `backend/token.json` and set it as the `GOOGLE_TOKEN_JSON` environment variable for production.

---

## Running Tests

```bash
cd backend
pytest tests/ -v --tb=short
```

**Test coverage:**

| Test File | What it covers |
|---|---|
| `test_sanitizer.py` | All 6 PII regex rules, body-length filtering, list helper |
| `test_classifier.py` | Domain mapping, batch parsing, Gemini error fallback |
| `test_summarizer.py` | Schema validation, word count ≤250, date formatting |
| `test_routes.py` | All REST endpoints — status codes, shapes, 404/409/422 |

---

## APScheduler Cron Configuration

The weekly pipeline runs automatically **every Sunday at 00:00 UTC**, configured in [`backend/app/scheduler.py`](backend/app/scheduler.py):

```python
scheduler.add_job(
    run_weekly_pipeline,
    trigger=CronTrigger(day_of_week="sun", hour=0, minute=0, timezone="UTC"),
)
```

**To change the schedule**, edit the `CronTrigger` arguments:
- `day_of_week` — `"mon"` through `"sun"`, or `"*"` for daily
- `hour` / `minute` — UTC time
- `timezone` — e.g., `"Asia/Kolkata"` for IST

---

## Re-running for a New Week

There are **three ways** to trigger a new weekly pulse:

### Option A — Dashboard (Recommended)

1. Open the dashboard at `http://localhost:5173` (or your Railway frontend URL)
2. Click the **"Trigger Pipeline"** button on the Dashboard page
3. Pick the **Start Date** and **End Date** for the review window you want to analyse (e.g., last 8 weeks: `2026-04-20` → `2026-06-15`)
4. Click **Run** — the pipeline stages will light up in real-time
5. When complete, the new pulse appears on the Dashboard and History page, plus a new Google Doc is created and a Gmail draft is staged

### Option B — API / cURL

Send a `POST` to the `/api/trigger` endpoint with a JSON body:

```bash
curl -X POST http://localhost:8000/api/trigger \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2026-04-20", "end_date": "2026-06-15"}'
```

Poll progress with:

```bash
curl http://localhost:8000/api/status
```

### Option C — Automatic (APScheduler Cron)

The pipeline runs automatically **every Sunday at 00:00 UTC** with an 8-week lookback window. No manual action required — just keep the backend service running.

### After the Run

| Artifact | Where to find it |
|---|---|
| Pulse JSON | `data/pulses/{run_id}.json` |
| Sanitized reviews | `data/reviews/{run_id}.json` |
| Google Doc | Link in Dashboard → "Workspace Artifacts" section |
| Gmail draft | Check your Gmail Drafts folder |
| Pipeline logs | Dashboard → Logs page, or `data/logs.jsonl` |

> **Tip:** To export the latest pulse as Markdown, see [`docs/weekly_pulse_latest.md`](docs/weekly_pulse_latest.md) for the format. You can automate this by reading `/api/pulses/{run_id}` and formatting the JSON.

---

## Submission Deliverables

| Deliverable | Location |
|---|---|
| Working prototype | Run locally (see Quick Start) or deploy to Railway (see below) |
| Latest weekly note | [`docs/weekly_pulse_latest.md`](docs/weekly_pulse_latest.md) + [Google Doc](https://docs.google.com/document/d/16ZQ9S8UNzV3N7HClZKD2S0tZTSbjn5x-4yzFzk9xVyQ/edit) |
| Email draft | [`docs/email_draft.md`](docs/email_draft.md) (text export) + Gmail draft ID `r2419843641344240281` |
| Reviews CSV | [`docs/sample_reviews.csv`](docs/sample_reviews.csv) — 51 redacted reviews (26 iOS + 25 Android) |
| Theme legend | See "Classification Domain Legend" section below |
| How to re-run | See "Re-running for a New Week" section above |

---

## Railway Deployment

Two services in a single Railway project (monorepo):

### Service 1: `lip5-api` (Backend)

| Setting | Value |
|---|---|
| Root Directory | `backend/` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

**Environment Variables to set in Railway (Recommended Approach):**

```
GEMINI_API_KEY=<your key>
GOOGLE_TOKEN_JSON=<raw contents of token.json generated locally>
GROWW_PACKAGE_NAME=com.nextbillion.groww
CORS_ORIGINS=https://your-frontend.up.railway.app
DATA_DIR=/data
```

*Note: By setting `GOOGLE_TOKEN_JSON`, you do not need to mount any secret files or configure client secrets.*

**Alternative Approach (Secret Files to mount):**

**Environment Variables:**
```
GEMINI_API_KEY=<your key>
GOOGLE_CLIENT_SECRETS_FILE=/etc/secrets/credentials.json
GROWW_PACKAGE_NAME=com.nextbillion.groww
CORS_ORIGINS=https://your-frontend.up.railway.app
DATA_DIR=/data
```

**Secret Files to mount:**
- `credentials.json` → `/etc/secrets/credentials.json`
- `token.json` → `/etc/secrets/token.json` *(generated locally first)*

### Service 2: `lip5-frontend` (Static)

| Setting | Value |
|---|---|
| Root Directory | `frontend/` |
| Build Command | `npm install && npm run build` |
| Publish Directory | `dist/` |
| Static Site | ✅ Yes |

**Environment Variable:**
```
VITE_API_URL=https://your-backend.up.railway.app
```

---

## Classification Domain Legend

Every review is assigned to exactly **one** of these 5 domains (or "Other"):

| Domain | Example Signals | Edge-Case Routing |
|---|---|---|
| **Order Execution & Latency** | Options slippage, delayed limit orders, chart mismatches, P&L errors | Routing/latency complaints about trades → here, even if support is mentioned |
| **Payments & Funding** | UPI failures, bank deposit issues, withdrawal delays, settlement cycles | "Money deducted but not credited" → here (not KYC) |
| **KYC & Onboarding** | PAN/Aadhaar verification, re-KYC, account creation blocks | Document re-upload loops → here even if framed as support failure |
| **Customer Support Quality** | Slow ticket resolution, bot loops, agent unresponsiveness | "Support never replies" without product issue → here |
| **App Stability & UI** | Crashes, freezes at 9:15 AM, biometric bugs, UI misalignment | Performance issues → here; if crash causes a missed trade → App Stability (not Order Execution) |
| **Other** | Regulatory complaints, general praise, off-topic | Gemini fallback when confidence is low |

---

## Sample Reviews Dataset

`docs/sample_reviews.csv` contains 25–50 redacted reviews covering all 5 domains:
- **Android reviews** scraped via `google-play-scraper` (real data, PII stripped)
- **iOS reviews** — 25 pre-authored realistic entries with `platform: "iOS"`, randomly spread across the review window

> **Why simulated iOS?** `google-play-scraper` is Android-only. App Store Connect requires developer credentials for review access. The 25 pre-authored iOS entries satisfy the mixed-platform submission requirement and match real Groww complaint patterns.

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check — returns `{"status": "ok"}` |
| `GET` | `/api/pulses` | List all historical pulse summaries |
| `GET` | `/api/pulses/{run_id}` | Full pulse detail including Doc URL and draft ID |
| `POST` | `/api/trigger` | Manually trigger pipeline for a date range |
| `GET` | `/api/status` | Live pipeline stage statuses |
| `GET` | `/api/logs` | Paginated logs (polled every 5s by dashboard) |

Interactive docs: `http://localhost:8000/docs`

---

## Flat-File Storage

Data is stored in `DATA_DIR/` (default: `backend/data/`):

```
data/
├── reviews/      {run_id}.json    — sanitized review arrays
├── pulses/       {run_id}.json    — full PulseDetail objects
└── logs.jsonl                     — append-only JSONL log stream
```

> **Supabase migration path:** Swap `backend/app/storage/store.py` for a Supabase client — all callers remain unchanged since the interface is the same.

---

## Verification Checklist

| Check | Command / Action |
|---|---|
| ✅ Server starts cleanly | `uvicorn app.main:app --reload` — no import errors |
| ✅ All tests pass | `pytest tests/ -v` — 0 failures |
| ✅ OAuth token saved | `python -m app.workspace.google_auth` → `token.json` created |
| ✅ Manual trigger works | `POST /api/trigger` → Doc in Drive + draft in Gmail inbox |
| ✅ Reviews sanitized | `data/reviews/<run_id>.json` contains no PII patterns |
| ✅ Log polling works | Logs page refreshes every 5s with new pipeline entries |
| ✅ Railway services live | Both services green in Railway dashboard |
