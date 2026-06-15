# LIP5 — Full Setup & Run Guide

> **Stack:** Python 3.11 · FastAPI · React + Vite · Gemini 1.5 Flash · Google Docs/Gmail API

This document walks you through every step needed to go from a fresh clone to a fully running LIP5 instance — backend API, React dashboard, and Google Workspace integration.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repository](#2-clone-the-repository)
3. [Google Cloud Platform Setup](#3-google-cloud-platform-setup)
4. [Gemini API Key](#4-gemini-api-key)
5. [Backend Setup](#5-backend-setup)
6. [Generate the Google OAuth Token](#6-generate-the-google-oauth-token)
7. [Run the Backend](#7-run-the-backend)
8. [Frontend Setup](#8-frontend-setup)
9. [Run the Frontend](#9-run-the-frontend)
10. [Run the Tests](#10-run-the-tests)
11. [Using the Dashboard](#11-using-the-dashboard)
12. [Triggering the Pipeline via API](#12-triggering-the-pipeline-via-api)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Prerequisites

Install the following tools before you begin.

| Tool | Minimum Version | Check |
|---|---|---|
| Python | 3.11 | `python --version` |
| Node.js | 18.x | `node --version` |
| npm | 9.x | `npm --version` |
| Git | any | `git --version` |

> **Windows users:** All commands below are written for **PowerShell**. Use the PowerShell equivalents where noted.

---

## 2. Clone the Repository

```bash
git clone https://github.com/your-org/LIP5.git
cd LIP5
```

The project has this top-level structure:

```
LIP5/
├── backend/    ← FastAPI API + pipeline logic
├── frontend/   ← React + Vite dashboard
└── docs/       ← documentation & sample data
```

---

## 3. Google Cloud Platform Setup

You need a GCP project with two APIs enabled, and an OAuth 2.0 credential for the Docs and Gmail integration.

### Step 3.1 — Create or Select a GCP Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Click the project dropdown at the top → **New Project**
3. Give it a name (e.g. `LIP5`) and click **Create**
4. Make sure this project is selected in the top bar

### Step 3.2 — Enable Required APIs

1. In the left sidebar go to **APIs & Services → Library**
2. Search for and enable each of these APIs:

   | API Name | Purpose |
   |---|---|
   | **Google Docs API** | Creates and formats the pulse report document |
   | **Gmail API** | Stages the email draft |

   For each: click the API → click **Enable**

### Step 3.3 — Configure the OAuth Consent Screen

Before creating credentials you must set up the consent screen.

1. Go to **APIs & Services → OAuth consent screen**
2. Select **External** → click **Create**
3. Fill in:
   - **App name:** `LIP5`
   - **User support email:** your email
   - **Developer contact:** your email
4. Click **Save and Continue** (scopes page — skip for now)
5. On the **Test users** page, click **Add Users** and add your own Google account email
6. Click **Save and Continue** → **Back to Dashboard**

> ⚠️ The app stays in "Testing" mode, which is fine for local development. Up to 100 test users can authorize it.

### Step 3.4 — Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Name: `LIP5 Local`
5. Click **Create**
6. In the dialog that appears, click **Download JSON**
7. Rename the downloaded file to **`credentials.json`**
8. Place it in the `backend/` folder:

```
LIP5/
└── backend/
    └── credentials.json   ← put it here
```

---

## 4. Gemini API Key

1. Go to [aistudio.google.com](https://aistudio.google.com/)
2. Click **Get API Key → Create API key**
3. Select your GCP project from the dropdown
4. Copy the generated key — you'll need it in Step 5.3

---

## 5. Backend Setup

### Step 5.1 — Create a Virtual Environment

```powershell
# From the LIP5 root directory
cd backend

python -m venv .venv
.venv\Scripts\Activate.ps1      # PowerShell
# source .venv/bin/activate     # macOS / Linux
```

You should see `(.venv)` in your terminal prompt.

### Step 5.2 — Install Python Dependencies

```powershell
pip install -r requirements.txt
```

This installs FastAPI, Uvicorn, APScheduler, Gemini SDK, Google API clients, google-play-scraper, and pytest.

### Step 5.3 — Create the `.env` File

Copy the example file and fill in your values:

```powershell
Copy-Item .env.example .env      # PowerShell
# cp .env.example .env           # macOS / Linux
```

Open `backend/.env` in any text editor and fill in:

```env
# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY=your_actual_gemini_key_here

# ── Google OAuth ──────────────────────────────────────────────────────────────
# Path to credentials.json you downloaded from GCP
GOOGLE_CLIENT_SECRETS_FILE=./credentials.json

# ── App Store ─────────────────────────────────────────────────────────────────
GROWW_PACKAGE_NAME=com.nextbillion.groww

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# ── Storage ───────────────────────────────────────────────────────────────────
DATA_DIR=./data
```

> **Important:** Never commit `.env` or `credentials.json` to Git. Both are already listed in `.gitignore`.

### Step 5.4 — Verify the Structure

Your `backend/` folder should now look like this:

```
backend/
├── .env                  ← created in step 5.3
├── .env.example
├── credentials.json      ← downloaded in step 3.4
├── Procfile
├── pyproject.toml
├── requirements.txt
├── app/
│   ├── main.py
│   ├── config.py
│   ├── scheduler.py
│   ├── analysis/
│   ├── api/
│   ├── ingestion/
│   ├── storage/
│   └── workspace/
└── tests/
```

---

## 6. Generate the Google OAuth Token

This is a **one-time step** that opens a browser to authorize the app and saves a `token.json` file.

> ⚠️ This must be run **locally** — the browser OAuth flow cannot run on a headless server like Railway.

Make sure your virtual environment is active, then from the `backend/` directory:

```powershell
python -m app.workspace.google_auth
```

**What happens:**
1. A browser window opens with a Google sign-in screen
2. Sign in with the Google account you added as a test user in Step 3.3
3. You'll see a consent screen listing the two permissions — click **Allow**
4. The terminal prints:

```
✅ OAuth token saved to: D:\...\backend\token.json
You can copy the contents of this file and set it as the GOOGLE_TOKEN_JSON environment variable.
```

A `token.json` file is now in the same folder as `credentials.json`. This token auto-refreshes — you won't need to repeat this step unless you revoke access or delete the file. For deployment on Railway, copy the entire JSON text from this file and set it as the `GOOGLE_TOKEN_JSON` environment variable.

---

## 7. Run the Backend

From the `backend/` directory (with `.venv` active):

```powershell
uvicorn app.main:app --reload
```

Expected output:

```
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     LIP5 backend starting up…
INFO:     APScheduler started (weekly pulse cron active).
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Verify the Backend is Running

Open these URLs in your browser:

| URL | Expected |
|---|---|
| `http://localhost:8000/api/health` | `{"status":"ok","version":"1.0.0",...}` |
| `http://localhost:8000/docs` | Interactive Swagger UI with all endpoints |
| `http://localhost:8000/api/status` | `{"status":"idle","stages":[...]}` |

---

## 8. Frontend Setup

Open a **new terminal window** (keep the backend running). From the `LIP5` root:

```powershell
cd frontend
npm install
```

### Step 8.1 — Create the Frontend `.env` File

```powershell
Copy-Item .env.example .env.local      # PowerShell
# cp .env.example .env.local           # macOS / Linux
```

The `.env.local` file should contain:

```env
VITE_API_URL=http://localhost:8000
```

This tells the React app where the backend API lives.

---

## 9. Run the Frontend

From the `frontend/` directory:

```powershell
npm run dev
```

Expected output:

```
  VITE v5.x.x  ready in ...ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

Open **[http://localhost:5173](http://localhost:5173)** in your browser. You should see the LIP5 dashboard with three navigation items: **Dashboard**, **History**, and **Logs**.

---

## 10. Run the Tests

In a terminal with the `.venv` active, from the `backend/` directory:

```powershell
python -m pytest tests/ -v --tb=short
```

Expected result:

```
========================= 98 passed, 0 warnings in 5.7s =========================
```

### What Each Test File Covers

| File | What is tested |
|---|---|
| `tests/test_sanitizer.py` | All 6 PII regex rules (email, phone, UPI, PAN, Aadhaar, tracker), body-length filtering, list helper |
| `tests/test_classifier.py` | Domain validation logic, Gemini batch parsing, markdown-fence stripping, error fallback to "Other" |
| `tests/test_summarizer.py` | Pulse schema shape, word count ≤ 250, `DD/MM/YYYY` date formatting, Gemini error fallback |
| `tests/test_routes.py` | All REST endpoints via FastAPI TestClient — HTTP status codes, response shapes, 404/409/422 |

To run a single file:

```powershell
python -m pytest tests/test_sanitizer.py -v
```

---

## 11. Using the Dashboard

With both services running, visit **[http://localhost:5173](http://localhost:5173)**.

### Dashboard Page (`/`)

- Shows the **current pipeline status** (idle / running / success / error)
- Displays **5 stage progress indicators** (Play Store Ingestion → Gmail Draft Staged)
- Contains the **Trigger Pipeline** panel — pick a date range and fire the pipeline manually
- Shows the **latest pulse themes** from the most recent successful run

### History Page (`/history`)

- Table of all past pulse runs
- Columns: Week Ending, Reviews Analyzed, Google Doc link, Created At
- Click any row's Doc link to open the generated Google Doc

### Logs Page (`/logs`)

- Terminal-style live log viewer
- **Polls `/api/logs` every 5 seconds** automatically
- Color-coded by level: INFO (white), WARNING (amber), ERROR (red)

---

## 12. Triggering the Pipeline via API

### Option A — Dashboard UI

1. Open the Dashboard at [http://localhost:5173](http://localhost:5173)
2. In the **Trigger Pipeline** panel, set a **Start Date** and **End Date**
3. Click **Run Pipeline**
4. Watch stage badges update in real time and switch to the Logs page to follow progress

### Option B — Direct API Call

Using curl:

```bash
curl -X POST http://localhost:8000/api/trigger \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-06-01", "end_date": "2024-06-07"}'
```

Using PowerShell:

```powershell
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/api/trigger" `
  -ContentType "application/json" `
  -Body '{"start_date":"2024-06-01","end_date":"2024-06-07"}'
```

**Response:**

```json
{
  "run_id": "a1b2c3d4e5f6",
  "status": "queued",
  "message": "Pipeline triggered. Poll /api/status for progress."
}
```

### Option C — Swagger UI

1. Open [http://localhost:8000/docs](http://localhost:8000/docs)
2. Expand **POST /api/trigger**
3. Click **Try it out** → fill in `start_date` and `end_date` → click **Execute**

### Pipeline Output

After a successful run:

| Output | Where to find it |
|---|---|
| Clean reviews JSON | `backend/data/reviews/<run_id>.json` |
| Pulse report JSON | `backend/data/pulses/<run_id>.json` |
| Google Doc | Link shown in History page / API response |
| Gmail Draft | Check your Gmail **Drafts** folder |
| Logs | `backend/data/logs.jsonl` or the Logs page |

---

## 13. Troubleshooting

### ❌ `uvicorn: command not found`

The virtual environment is not active. Run:

```powershell
.venv\Scripts\Activate.ps1
```

---

### ❌ `ModuleNotFoundError: No module named 'app'`

You must run `uvicorn` from inside the `backend/` directory, not from the project root:

```powershell
cd backend
uvicorn app.main:app --reload
```

---

### ❌ `FileNotFoundError: Google client secrets not found`

`credentials.json` is missing or in the wrong location. It must be in `backend/credentials.json`, and `GOOGLE_CLIENT_SECRETS_FILE=./credentials.json` must be set in `backend/.env`.

---

### ❌ `RuntimeError: No valid Google OAuth token found`

You haven't run the OAuth flow yet, or the token is missing/revoked. You can:
1. Run the local OAuth flow:
   ```powershell
   python -m app.workspace.google_auth
   ```
2. If deploying to Railway, configure the `GOOGLE_TOKEN_JSON` environment variable with the JSON contents of your locally generated `token.json` file.
3. If `token.json` exists but this error still occurs, the token may be expired or revoked. Delete the local `token.json` file (if any) and re-run the local auth flow command.

---

### ❌ `ValueError: GEMINI_API_KEY is not configured`

`GEMINI_API_KEY` is empty or missing from `backend/.env`. Open the file and paste your key.

---

### ❌ Pipeline runs but Google Doc is not created

- Confirm the **Google Docs API** is enabled in your GCP project (Step 3.2)
- Confirm `token.json` exists in the same folder as `credentials.json`
- Check the Logs page for a specific error message from the `Google Docs Sync` stage

---

### ❌ CORS error in browser console

The frontend origin is not in `CORS_ORIGINS`. Open `backend/.env` and ensure:

```env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

Then restart the backend.

---

### ❌ `npm run dev` fails — `ENOENT package.json`

You must run npm commands from inside the `frontend/` directory:

```powershell
cd frontend
npm run dev
```

---

### ❌ `409 Conflict` when triggering the pipeline

A run is already in progress. Wait for it to finish (check `/api/status`) or restart the backend to clear the in-memory state.

---

## Quick Reference — All Commands

```powershell
# ── Backend ────────────────────────────────────────────────────────────────────
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env          # then fill in GEMINI_API_KEY

# First-time OAuth token generation (once only)
python -m app.workspace.google_auth

# Start the API server
uvicorn app.main:app --reload

# Run all tests
python -m pytest tests/ -v --tb=short

# ── Frontend ───────────────────────────────────────────────────────────────────
cd frontend
npm install
Copy-Item .env.example .env.local    # VITE_API_URL=http://localhost:8000
npm run dev
```

---

*Both services must be running simultaneously: backend on `:8000`, frontend on `:5173`.*
