# 🚀 LIP Challenge 5: Automated App Store Pulse & Governance Workflow

**Product Context:** Groww (Wealth & Investment Platform)

**Infrastructure Stack:** Google Cloud Platform (GCP), Gmail API, Google Docs API, Python/Node.js

---

## 👥 Who This Helps

* **Product & Engineering Teams:** Instantly surface critical app latency, trade slippage, or payment drop-offs directly from real user store feedback.
* **Support & Operations:** Monitor recent spikes in customer service frustrations or transaction failures to proactively scale support queues.
* **Leadership:** Keep tabs on platform health via a structured, scannable weekly communication loop.

---

## 🏗️ Architecture & Full-Stack System Flow

You are building a full-stack internal tool that operates on a regular weekly cadence. The backend handles scheduled ingestion, AI-driven analysis, and automated Google Workspace synchronization, while the frontend serves as an operational dashboard for the product team.

```
┌────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                  │
│  - Review Dashboard  - Manual Ingestion Trigger  - System Log Viewer   │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTP API / Webhooks
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                   │
│  - Scheduled Cron (Weekly Trigger)                                     │
│  - Review Ingestion Engine (Google Play Store & App Store Pipelines)   │
│  - LLM Classification & Summarization Worker                           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Google Cloud APIs
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       GOOGLE WORKSPACE LAYER                           │
│  - Google Docs API (Generates Executive Pulse Artifact)                │
│  - Gmail API (Stages Formatted Draft Email to Self)                    │
└────────────────────────────────────────────────────────────────────────┘

```

---

## 📋 Comprehensive Problem Statement & Specification

### 1. Ingestion & Scheduled Automation

* **The Ingestion Pipelines:** The backend must support data retrieval from multiple platforms—primarily the **Google Play Store** and the **Apple App Store** (via automated exports, public feeds, or simulated historical drops).
* **The Weekly Trigger:** The system must run automatically on a weekly schedule (e.g., every Sunday at midnight). It should isolate and ingest records belonging strictly to the previous 7-day window.
* **The Corpus Schema:** Each ingested review row must map to: `rating`, `review_title`, `review_text`, `date`, and `platform` (iOS/Android).

### 2. The Full-Stack Application Interface

* **Backend Responsibilities:**
* Expose secure REST endpoints for the frontend to query historical pulses, trigger manual re-runs, and view processing logs.
* Maintain an asynchronous background worker to process the incoming text dataset through an LLM without blocking the main event loop.


* **Frontend Responsibilities:**
* Provide a clean dashboard displaying the current week's top themes, real-time sync statuses, and historical pulse generation logs.
* Include a manual "Trigger Run" button that bypasses the weekly schedule to process a specific date range on demand.



### 3. Core Analytical Classification

The backend worker passes the raw text records through a structured prompt to classify them into **a maximum of 5 core fintech domains**:

1. *Order Execution & Latency* (e.g., Options slippage, delayed limit orders, chart price mismatches)
2. *Payments & Funding* (e.g., Bank deposits, failures adding money, settlement cycles)
3. *KYC & Onboarding* (e.g., Account creation, document verification, re-KYC)
4. *Customer Support Quality* (e.g., Agent responsiveness, ticketing, automated loops)
5. *App Stability & UI* (e.g., Post-update bugs, crashes during market hours)

### 4. Automated Workspace Generation

* **Google Docs Integration:** Upon successful categorization, the backend connects to the **Google Docs API** to initialize, populate, and format an executive health document.
* **Content Blueprint:** The document must strictly adhere to a **maximum limit of 250 words** to remain readable for leadership, containing:
* **Top 3 Themes:** Highly specific trends identified during the week.
* **3 Verbatim User Quotes:** Real, unedited user text illustrating those exact themes.
* **3 Strategic Action Ideas:** Pragmatic engineering or operational fixes.


* **Aesthetic Rules:** The generated document should use structural formatting headers and high-contrast styling blocks to emphasize core KPIs and scannable thematic categories.


* **Gmail Integration:** The backend uses the **Gmail API** to stage a *Draft Email* inside your connected account's drafts folder containing the complete synthesized note.
* **Subject Line Format:** `[Weekly App Pulse] Groww Store Review Insights - Week Ending DD/MM/YYYY`



---

## ⚠️ Key Guardrails & Constraints

* **Absolute PII Sanitization:** Financial data privacy rules strictly apply. You must explicitly build a regex or LLM-based sanitization step. **Zero user-identifiable metrics** (usernames, email addresses, explicit phone numbers, or arbitrary account tracker strings) can enter the database, the Google Doc, or the Gmail Draft.
* **Public Sourcing Only:** Use only publicly available review exports or simulation data matching real Play/App Store metrics. No authenticated internal databases or scraped portals behind login gates.
* **Text-First Concise Formats:** Keep the final payload dense, precise, and highly scannable. Avoid conversational boilerplate ("Here is the report you requested"). Lead straight with the insights.

---

## 📦 Submission Deliverables

To complete this system integration from scratch, your project repository must contain:

1. **Full-Stack Codebase:**
* **Backend:** Script or application code utilizing authenticated GCP service accounts or OAuth client profiles managing your `google-api-python-client` (or Node equivalent) operations.
* **Frontend:** Source files for your internal application dashboard.


2. **Live Artifact Proofs:**
* An exported markdown file or link showing the layout of your **Google Doc Weekly Pulse**.
* A clean text copy or snapshot of the **Gmail Draft Email** correctly staged in your inbox.


3. **Reviews Dataset:** A sample of 25-50 rows of redacted store reviews (combining Android and iOS) used to validate your automation pipeline.
4. **README Architecture Guide:**
* Setup instructions detailing GCP console configurations (Scopes needed: `[https://www.googleapis.com/auth/documents](https://www.googleapis.com/auth/documents)`, `[https://www.googleapis.com/auth/gmail.compose](https://www.googleapis.com/auth/gmail.compose)`).
* Configuration steps for the automated weekly cron trigger.
* A concise **Theme Legend** mapping how edge-case reviews are sorted by your LLM routing logic.



---

### 🧠 Verified Skills Being Tested

* **Full-Stack & Pipeline Engineering:** Building a client-server interface that coordinates scheduled jobs, background worker cycles, and reliable data pipelines.
* **Data Summarization & Intent Extraction:** Distilling chaotic, repetitive mobile feedback into core architectural and operational action points.
* **GCP Integration Engineering:** Working directly with OAuth/Service Account workflows, constructing batch requests for the Google Docs document service, and managing raw MIME email strings for the Gmail endpoint.

---