"""
routes.py — All REST endpoints + pipeline orchestrator.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.api.schemas import (
    HealthResponse,
    LogsResponse,
    PulseDetail,
    PulsesResponse,
    StatusResponse,
    TriggerRequest,
    TriggerResponse,
)
from app.storage.store import (
    append_log,
    finish_run,
    get_run_status,
    list_pulses,
    load_pulse,
    new_run_id,
    read_logs,
    reset_run_state,
    save_reviews,
    update_stage,
)

router = APIRouter(prefix="/api")


# ── Health ─────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse()


# ── Pulses ─────────────────────────────────────────────────────────────────────

@router.get("/pulses", response_model=PulsesResponse, tags=["pulses"])
async def get_pulses() -> PulsesResponse:
    pulses = list_pulses()
    return PulsesResponse(pulses=pulses, total=len(pulses))


@router.get("/pulses/{run_id}", response_model=PulseDetail, tags=["pulses"])
async def get_pulse(run_id: str) -> PulseDetail:
    pulse = load_pulse(run_id)
    if pulse is None:
        raise HTTPException(status_code=404, detail=f"Pulse '{run_id}' not found.")
    return pulse


# ── Status ─────────────────────────────────────────────────────────────────────

@router.get("/status", response_model=StatusResponse, tags=["pipeline"])
async def get_status() -> StatusResponse:
    return get_run_status()


# ── Logs ───────────────────────────────────────────────────────────────────────

@router.get("/logs", response_model=LogsResponse, tags=["pipeline"])
async def get_logs(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> LogsResponse:
    entries, total = read_logs(page=page, page_size=page_size)
    return LogsResponse(entries=entries, total=total, page=page, page_size=page_size)


# ── Trigger ────────────────────────────────────────────────────────────────────

@router.post("/trigger", response_model=TriggerResponse, status_code=202, tags=["pipeline"])
async def trigger_pipeline(
    body: TriggerRequest,
    background_tasks: BackgroundTasks,
) -> TriggerResponse:
    current = get_run_status()
    if current.status == "running":
        raise HTTPException(status_code=409, detail="A pipeline run is already in progress.")

    run_id = new_run_id()
    reset_run_state(run_id)
    append_log("Pipeline triggered via API", run_id=run_id, extra={"start": body.start_date, "end": body.end_date})
    background_tasks.add_task(_run_pipeline, run_id, body.start_date, body.end_date)
    return TriggerResponse(run_id=run_id)


# ── Pipeline orchestrator ──────────────────────────────────────────────────────

async def _run_pipeline(run_id: str, start_date: str, end_date: str) -> None:
    """
    Full pipeline orchestrator. Each phase is imported lazily so that
    missing credentials/packages cause a graceful error, not a startup crash.
    """
    append_log(f"Pipeline starting for {start_date} → {end_date}", run_id=run_id)

    try:
        # ── Stage 1: Play Store Ingestion ──────────────────────────────────────
        update_stage("Play Store Ingestion", "running")
        append_log("Fetching Play Store reviews…", run_id=run_id)
        try:
            from app.ingestion.play_store import fetch_reviews  # noqa: PLC0415
            reviews = await asyncio.to_thread(fetch_reviews, start_date, end_date)
            append_log(f"Fetched {len(reviews)} reviews (pre-sanitization).", run_id=run_id)
            update_stage("Play Store Ingestion", "success", detail=f"{len(reviews)} reviews fetched")
        except Exception as exc:  # noqa: BLE001
            update_stage("Play Store Ingestion", "error", detail=str(exc))
            append_log(f"Ingestion error: {exc}", level="ERROR", run_id=run_id)
            finish_run("error", error=str(exc))
            return

        # ── Stage 2: PII Sanitization ──────────────────────────────────────────
        update_stage("PII Sanitization", "running")
        append_log("Sanitizing reviews…", run_id=run_id)
        try:
            from app.ingestion.sanitizer import sanitize_reviews  # noqa: PLC0415
            clean_reviews = sanitize_reviews(reviews)
            save_reviews(run_id, clean_reviews)
            append_log(
                f"Sanitization complete. {len(clean_reviews)}/{len(reviews)} reviews kept.",
                run_id=run_id,
            )
            update_stage("PII Sanitization", "success", detail=f"{len(clean_reviews)} clean reviews saved")
        except Exception as exc:  # noqa: BLE001
            update_stage("PII Sanitization", "error", detail=str(exc))
            append_log(f"Sanitization error: {exc}", level="ERROR", run_id=run_id)
            finish_run("error", error=str(exc))
            return

        # ── Stage 3: Gemini Classification ────────────────────────────────────
        update_stage("Gemini Classification", "running")
        append_log("Running Gemini classification…", run_id=run_id)
        try:
            from app.analysis.classifier import classify_reviews  # noqa: PLC0415
            classified = await asyncio.to_thread(classify_reviews, clean_reviews)
            append_log(f"Classification complete for {len(classified)} reviews.", run_id=run_id)
            update_stage("Gemini Classification", "success", detail=f"{len(classified)} classified")
        except Exception as exc:  # noqa: BLE001
            update_stage("Gemini Classification", "error", detail=str(exc))
            append_log(f"Classification error: {exc}", level="ERROR", run_id=run_id)
            finish_run("error", error=str(exc))
            return

        # ── Stage 4: Gemini Summarization ──────────────────────────────────────
        update_stage("Gemini Summarization", "running")
        append_log("Generating pulse summary…", run_id=run_id)
        try:
            from app.analysis.summarizer import generate_pulse  # noqa: PLC0415
            pulse_data = await asyncio.to_thread(generate_pulse, classified, end_date, run_id)
            append_log("Pulse summary generated.", run_id=run_id)
            update_stage("Gemini Summarization", "success")
        except Exception as exc:  # noqa: BLE001
            update_stage("Gemini Summarization", "error", detail=str(exc))
            append_log(f"Summarization error: {exc}", level="ERROR", run_id=run_id)
            finish_run("error", error=str(exc))
            return

        # ── Stage 5: Google Docs Sync ──────────────────────────────────────────
        update_stage("Google Docs Sync", "running")
        append_log("Pushing to Google Docs…", run_id=run_id)
        doc_url: str | None = None
        try:
            from app.workspace.docs_writer import write_pulse_doc  # noqa: PLC0415
            doc_url = await asyncio.to_thread(write_pulse_doc, pulse_data)
            pulse_data.google_doc_url = doc_url
            append_log(f"Google Doc created: {doc_url}", run_id=run_id)
            update_stage("Google Docs Sync", "success", detail=doc_url)
        except Exception as exc:  # noqa: BLE001
            update_stage("Google Docs Sync", "error", detail=str(exc))
            append_log(f"Docs error: {exc}", level="WARNING", run_id=run_id)
            # Non-fatal — continue to Gmail

        # ── Stage 6: Gmail Draft ──────────────────────────────────────────────
        update_stage("Gmail Draft Staged", "running")
        append_log("Staging Gmail draft…", run_id=run_id)
        try:
            from app.workspace.gmail_drafter import stage_draft  # noqa: PLC0415
            draft_id = await asyncio.to_thread(stage_draft, pulse_data, doc_url)
            pulse_data.gmail_draft_id = draft_id
            append_log(f"Gmail draft staged: {draft_id}", run_id=run_id)
            update_stage("Gmail Draft Staged", "success", detail=draft_id)
        except Exception as exc:  # noqa: BLE001
            update_stage("Gmail Draft Staged", "error", detail=str(exc))
            append_log(f"Gmail error: {exc}", level="WARNING", run_id=run_id)
            # Non-fatal

        # ── Persist final pulse ────────────────────────────────────────────────
        from app.storage.store import save_pulse  # noqa: PLC0415
        save_pulse(pulse_data)
        finish_run("success")
        append_log("Pipeline completed successfully.", run_id=run_id)

    except Exception as exc:  # noqa: BLE001
        finish_run("error", error=str(exc))
        append_log(f"Unhandled pipeline error: {exc}", level="ERROR", run_id=run_id)
