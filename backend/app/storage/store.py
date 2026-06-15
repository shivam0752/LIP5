"""
store.py — Flat-file helpers: reviews, pulses, logs, and pipeline run-state tracker.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings
from app.api.schemas import (
    LogEntry,
    PulseDetail,
    PulseSummary,
    RunStatus,
    StatusResponse,
    PipelineStage,
)


# ── Internal run-state (in-memory, single-process) ─────────────────────────────

_current_status: StatusResponse = StatusResponse()


def get_run_status() -> StatusResponse:
    return _current_status


def reset_run_state(run_id: str) -> None:
    global _current_status
    _current_status = StatusResponse(
        run_id=run_id,
        status="running",
        started_at=datetime.utcnow(),
        stages=[
            PipelineStage(name="Play Store Ingestion"),
            PipelineStage(name="PII Sanitization"),
            PipelineStage(name="Gemini Classification"),
            PipelineStage(name="Gemini Summarization"),
            PipelineStage(name="Google Docs Sync"),
            PipelineStage(name="Gmail Draft Staged"),
        ],
    )


def update_stage(stage_name: str, status: RunStatus, detail: Optional[str] = None) -> None:
    global _current_status
    for stage in _current_status.stages:
        if stage.name == stage_name:
            stage.status = status
            stage.detail = detail
            break


def finish_run(status: RunStatus, error: Optional[str] = None) -> None:
    global _current_status
    _current_status.status = status
    _current_status.finished_at = datetime.utcnow()
    _current_status.error = error


# ── Reviews ────────────────────────────────────────────────────────────────────

def save_reviews(run_id: str, reviews: list[dict[str, Any]]) -> Path:
    settings = get_settings()
    settings.ensure_dirs()
    dest = settings.reviews_path / f"{run_id}.json"
    dest.write_text(json.dumps(reviews, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest


def load_reviews(run_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    dest = settings.reviews_path / f"{run_id}.json"
    if not dest.exists():
        return []
    return json.loads(dest.read_text(encoding="utf-8"))


# ── Pulses ─────────────────────────────────────────────────────────────────────

def save_pulse(pulse: PulseDetail) -> Path:
    settings = get_settings()
    settings.ensure_dirs()
    dest = settings.pulses_path / f"{pulse.run_id}.json"
    dest.write_text(
        pulse.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return dest


def load_pulse(run_id: str) -> Optional[PulseDetail]:
    settings = get_settings()
    dest = settings.pulses_path / f"{run_id}.json"
    if not dest.exists():
        return None
    return PulseDetail.model_validate_json(dest.read_text(encoding="utf-8"))


def list_pulses() -> list[PulseSummary]:
    settings = get_settings()
    settings.ensure_dirs()
    summaries: list[PulseSummary] = []
    for f in sorted(settings.pulses_path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            pulse = PulseDetail.model_validate_json(f.read_text(encoding="utf-8"))
            summaries.append(
                PulseSummary(
                    run_id=pulse.run_id,
                    week_ending=pulse.week_ending,
                    total_reviews_analyzed=pulse.total_reviews_analyzed,
                    google_doc_url=pulse.google_doc_url,
                    created_at=pulse.created_at,
                )
            )
        except Exception:
            continue
    return summaries


# ── Logs ───────────────────────────────────────────────────────────────────────

def append_log(
    message: str,
    level: str = "INFO",
    run_id: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    settings = get_settings()
    settings.ensure_dirs()
    entry = LogEntry(
        ts=datetime.utcnow(),
        level=level,  # type: ignore[arg-type]
        message=message,
        run_id=run_id,
        extra=extra,
    )
    with settings.logs_path.open("a", encoding="utf-8") as fh:
        fh.write(entry.model_dump_json() + "\n")


def read_logs(page: int = 1, page_size: int = 50) -> tuple[list[LogEntry], int]:
    """Return paginated log entries (newest first)."""
    settings = get_settings()
    if not settings.logs_path.exists():
        return [], 0
    raw_lines = settings.logs_path.read_text(encoding="utf-8").splitlines()
    total = len(raw_lines)
    # Reverse so newest entries appear first
    reversed_lines = list(reversed(raw_lines))
    start = (page - 1) * page_size
    end = start + page_size
    entries: list[LogEntry] = []
    for line in reversed_lines[start:end]:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(LogEntry.model_validate_json(line))
        except Exception:
            continue
    return entries, total


# ── Utility ────────────────────────────────────────────────────────────────────

def new_run_id() -> str:
    return uuid.uuid4().hex[:12]
