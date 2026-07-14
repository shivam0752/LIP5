"""
test_routes.py — FastAPI TestClient tests for all REST endpoints.

Tests use an in-memory app instance with the data dir overridden
to a temp directory. External calls (Gemini, Google APIs) are never
made — background pipeline tasks are patched out.

Coverage:
  GET  /api/health        — returns 200 + ok status + version
  GET  /api/status        — returns idle state initially
  GET  /api/logs          — returns empty log list when no logs exist
  GET  /api/pulses        — returns empty list initially; list after save
  GET  /api/pulses/{id}   — 200 for existing, 404 for missing
  POST /api/trigger       — 202 accepted; 409 when already running
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.schemas import (
    ActionIdea,
    PulseDetail,
    ThemeSummary,
    VerbatimQuote,
)
from app.storage.store import reset_run_state, save_pulse


@pytest.fixture()
def client(tmp_data_dir: Path) -> TestClient:
    """Return a TestClient with scheduler startup suppressed."""
    # Reset global run state before each test
    from app.storage import store as store_module
    store_module._current_status.__init__()  # reset to idle

    with patch("app.scheduler.scheduler") as mock_scheduler:
        mock_scheduler.start = MagicMock()
        mock_scheduler.shutdown = MagicMock()
        from app.main import create_app
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


@pytest.fixture()
def sample_pulse(tmp_data_dir: Path) -> PulseDetail:
    """Create and persist a sample pulse, return it."""
    pulse = PulseDetail(
        run_id="run-123",
        timeline="01/06/2024 to 07/06/2024",
        total_reviews_analyzed=100,
        executive_summary="Overall sentiment is mixed with prominent App Stability concerns.",
        domain_distribution={
            "App Stability & UI": 40,
            "Payments & Funding": 30,
            "KYC & Onboarding": 10,
            "Customer Support Quality": 10,
            "Order Execution & Latency": 5,
            "Other": 5
        },
        sentiment_breakdown={
            "positive": 40,
            "neutral": 20,
            "negative": 40
        },
        top_themes=[
            ThemeSummary(domain="App Stability & UI", summary="Users report crashes at market open."),
            ThemeSummary(domain="Payments & Funding", summary="UPI failures causing fund delays."),
            ThemeSummary(domain="Customer Support Quality", summary="Bot loops frustrate users."),
        ],
        verbatim_quotes=[
            VerbatimQuote(quote="App crashes every 9 AM.", domain="App Stability & UI", rating=1),
            VerbatimQuote(quote="UPI deducted but not credited.", domain="Payments & Funding", rating=1),
            VerbatimQuote(quote="Chatbot is useless.", domain="Customer Support Quality", rating=2),
        ],
        action_ideas=[
            ActionIdea(action="Fix market-open crash spikes.", domain="App Stability & UI"),
            ActionIdea(action="Add UPI auto-reconciliation.", domain="Payments & Funding"),
            ActionIdea(action="Reduce P1 SLA to 4 hours.", domain="Customer Support Quality"),
        ],
        google_doc_url="https://docs.google.com/document/d/test",
        gmail_draft_id="draft-abc123",
        created_at=datetime(2024, 6, 7, 12, 0, 0),
    )
    save_pulse(pulse)
    return pulse


# ── Health ─────────────────────────────────────────────────────────────────────


class TestHealth:
    def test_returns_200(self, client: TestClient):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_status_is_ok(self, client: TestClient):
        data = client.get("/api/health").json()
        assert data["status"] == "ok"

    def test_version_field_present(self, client: TestClient):
        data = client.get("/api/health").json()
        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_timestamp_field_present(self, client: TestClient):
        data = client.get("/api/health").json()
        assert "timestamp" in data


# ── Status ─────────────────────────────────────────────────────────────────────


class TestStatus:
    def test_returns_200(self, client: TestClient):
        resp = client.get("/api/status")
        assert resp.status_code == 200

    def test_idle_status_initially(self, client: TestClient):
        data = client.get("/api/status").json()
        assert data["status"] == "idle"

    def test_status_has_stages_field(self, client: TestClient):
        data = client.get("/api/status").json()
        assert "stages" in data


# ── Logs ───────────────────────────────────────────────────────────────────────


class TestLogs:
    def test_returns_200(self, client: TestClient):
        resp = client.get("/api/logs")
        assert resp.status_code == 200

    def test_response_shape(self, client: TestClient):
        data = client.get("/api/logs").json()
        assert "entries" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_pagination_params_accepted(self, client: TestClient):
        resp = client.get("/api/logs?page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_invalid_page_returns_422(self, client: TestClient):
        resp = client.get("/api/logs?page=0")
        assert resp.status_code == 422


# ── Pulses ─────────────────────────────────────────────────────────────────────


class TestPulses:
    def test_empty_list_initially(self, client: TestClient):
        data = client.get("/api/pulses").json()
        assert data["pulses"] == []
        assert data["total"] == 0

    def test_returns_200(self, client: TestClient):
        resp = client.get("/api/pulses")
        assert resp.status_code == 200

    def test_saved_pulse_appears_in_list(self, client: TestClient, sample_pulse: PulseDetail):
        data = client.get("/api/pulses").json()
        assert data["total"] == 1
        assert data["pulses"][0]["run_id"] == sample_pulse.run_id

    def test_pulse_detail_200(self, client: TestClient, sample_pulse: PulseDetail):
        resp = client.get(f"/api/pulses/{sample_pulse.run_id}")
        assert resp.status_code == 200

    def test_pulse_detail_contains_correct_data(self, client: TestClient, sample_pulse: PulseDetail):
        data = client.get(f"/api/pulses/{sample_pulse.run_id}").json()
        assert data["run_id"] == sample_pulse.run_id
        assert data["timeline"] == sample_pulse.timeline
        assert data["total_reviews_analyzed"] == sample_pulse.total_reviews_analyzed
        assert len(data["top_themes"]) == 3
        assert len(data["verbatim_quotes"]) == 3
        assert len(data["action_ideas"]) == 3

    def test_pulse_google_doc_url_present(self, client: TestClient, sample_pulse: PulseDetail):
        data = client.get(f"/api/pulses/{sample_pulse.run_id}").json()
        assert data["google_doc_url"] == sample_pulse.google_doc_url

    def test_missing_pulse_returns_404(self, client: TestClient):
        resp = client.get("/api/pulses/nonexistent-run-id")
        assert resp.status_code == 404


# ── Trigger ────────────────────────────────────────────────────────────────────


class TestTrigger:
    def _trigger(self, client: TestClient, start: str = "2024-06-01", end: str = "2024-06-07"):
        return client.post(
            "/api/trigger",
            json={"start_date": start, "end_date": end},
        )

    def test_accepted_202(self, client: TestClient):
        with patch("app.api.routes._run_pipeline", new=AsyncMock()):
            resp = self._trigger(client)
        assert resp.status_code == 202

    def test_returns_run_id(self, client: TestClient):
        with patch("app.api.routes._run_pipeline", new=AsyncMock()):
            data = self._trigger(client).json()
        assert "run_id" in data
        assert len(data["run_id"]) > 0

    def test_status_queued(self, client: TestClient):
        with patch("app.api.routes._run_pipeline", new=AsyncMock()):
            data = self._trigger(client).json()
        assert data["status"] == "queued"

    def test_missing_fields_returns_422(self, client: TestClient):
        resp = client.post("/api/trigger", json={"start_date": "2024-06-01"})
        assert resp.status_code == 422

    def test_409_when_already_running(self, client: TestClient):
        # Manually set state to running
        reset_run_state("existing-run")
        resp = self._trigger(client)
        assert resp.status_code == 409
