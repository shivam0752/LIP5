"""
schemas.py — Pydantic request/response models for the LIP5 API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ── Generic ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Trigger ────────────────────────────────────────────────────────────────────

class TriggerRequest(BaseModel):
    start_date: str = Field(
        ...,
        description="Start of review window (YYYY-MM-DD)",
        examples=["2024-06-01"],
    )
    end_date: str = Field(
        ...,
        description="End of review window (YYYY-MM-DD)",
        examples=["2024-06-07"],
    )


class TriggerResponse(BaseModel):
    run_id: str
    status: Literal["queued"] = "queued"
    message: str = "Pipeline triggered. Poll /api/status for progress."


# ── Status ─────────────────────────────────────────────────────────────────────

RunStatus = Literal["idle", "running", "success", "error"]


class PipelineStage(BaseModel):
    name: str
    status: RunStatus = "idle"
    detail: Optional[str] = None


class StatusResponse(BaseModel):
    run_id: Optional[str] = None
    status: RunStatus = "idle"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    stages: list[PipelineStage] = Field(default_factory=list)
    error: Optional[str] = None


# ── Pulse ──────────────────────────────────────────────────────────────────────

class ThemeSummary(BaseModel):
    domain: str
    summary: str


class VerbatimQuote(BaseModel):
    quote: str
    domain: str
    rating: int


class ActionIdea(BaseModel):
    action: str
    domain: str


class PulseDetail(BaseModel):
    run_id: str
    week_ending: str
    total_reviews_analyzed: int
    executive_summary: str
    domain_distribution: dict[str, int]
    sentiment_breakdown: dict[str, int]
    top_themes: list[ThemeSummary]
    verbatim_quotes: list[VerbatimQuote]
    action_ideas: list[ActionIdea]
    google_doc_url: Optional[str] = None
    gmail_draft_id: Optional[str] = None
    created_at: datetime


class PulseSummary(BaseModel):
    run_id: str
    week_ending: str
    total_reviews_analyzed: int
    google_doc_url: Optional[str] = None
    created_at: datetime


class PulsesResponse(BaseModel):
    pulses: list[PulseSummary]
    total: int


# ── Logs ───────────────────────────────────────────────────────────────────────

class LogEntry(BaseModel):
    ts: datetime
    level: Literal["INFO", "WARNING", "ERROR", "DEBUG"]
    message: str
    run_id: Optional[str] = None
    extra: Optional[dict[str, Any]] = None


class LogsResponse(BaseModel):
    entries: list[LogEntry]
    total: int
    page: int
    page_size: int
