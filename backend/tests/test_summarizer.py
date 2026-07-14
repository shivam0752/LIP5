"""
test_summarizer.py — Unit tests for the Gemini pulse summarizer.

All Gemini API calls are mocked. Tests verify:
  - Output conforms to PulseDetail schema (required keys present)
  - Top-level word count of summaries + action descriptions ≤ 250
  - Fallback pulse is used when Gemini fails
  - timeline is formatted as DD/MM/YYYY to DD/MM/YYYY
  - total_reviews_analyzed matches input count
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.analysis.summarizer import _call_gemini, _fallback_pulse, generate_pulse
from app.api.schemas import PulseDetail


@pytest.fixture()
def valid_pulse_json() -> str:
    return json.dumps({
        "executive_summary": "Overall app sentiment this week is mixed.",
        "top_themes": [
            {"domain": "App Stability & UI", "summary": "Theme 1"},
            {"domain": "Payments & Funding", "summary": "Theme 2"},
            {"domain": "KYC & Onboarding", "summary": "Theme 3"},
        ],
        "verbatim_quotes": [
            {"quote": "Quote 1", "domain": "App Stability & UI", "rating": 1},
            {"quote": "Quote 2", "domain": "Payments & Funding", "rating": 2},
            {"quote": "Quote 3", "domain": "KYC & Onboarding", "rating": 3},
        ],
        "action_ideas": [
            {"action": "Action 1", "domain": "App Stability & UI"},
            {"action": "Action 2", "domain": "Payments & Funding"},
            {"action": "Action 3", "domain": "KYC & Onboarding"},
        ]
    })


# ── _fallback_pulse ───────────────────────────────────────────────────────────


class TestFallbackPulse:
    def test_required_keys_present(self):
        pulse = _fallback_pulse([], "2024-06-01", "2024-06-07")
        assert "top_themes" in pulse
        assert "verbatim_quotes" in pulse
        assert "action_ideas" in pulse

    def test_three_items_per_section(self):
        pulse = _fallback_pulse([], "2024-06-01", "2024-06-07")
        assert len(pulse["top_themes"]) == 3
        assert len(pulse["verbatim_quotes"]) == 3
        assert len(pulse["action_ideas"]) == 3

    def test_theme_structure(self):
        pulse = _fallback_pulse([], "2024-06-01", "2024-06-07")
        for theme in pulse["top_themes"]:
            assert "domain" in theme
            assert "summary" in theme
            assert isinstance(theme["summary"], str)
            assert len(theme["summary"]) > 0

    def test_quote_structure(self):
        pulse = _fallback_pulse([], "2024-06-01", "2024-06-07")
        for quote in pulse["verbatim_quotes"]:
            assert "quote" in quote
            assert "domain" in quote
            assert "rating" in quote
            assert 1 <= quote["rating"] <= 5

    def test_action_structure(self):
        pulse = _fallback_pulse([], "2024-06-01", "2024-06-07")
        for action in pulse["action_ideas"]:
            assert "action" in action
            assert "domain" in action

    def test_word_count_under_250(self):
        pulse = _fallback_pulse([], "2024-06-01", "2024-06-07")
        words = []
        for t in pulse["top_themes"]:
            words.extend(t["summary"].split())
        for a in pulse["action_ideas"]:
            words.extend(a["action"].split())
        assert len(words) <= 250, f"Word count {len(words)} exceeds 250"


# ── _call_gemini ──────────────────────────────────────────────────────────────


class TestCallGemini:
    def _make_model(self, json_text: str) -> MagicMock:
        mock_response = MagicMock()
        mock_response.text = json_text
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        return mock_model

    def test_valid_json_response_parsed(self):
        payload = _fallback_pulse([], "2024-06-01", "2024-06-07")
        model = self._make_model(json.dumps(payload))
        result = _call_gemini(model, "test prompt")
        assert "top_themes" in result
        assert "verbatim_quotes" in result
        assert "action_ideas" in result

    def test_markdown_fences_stripped(self):
        payload = _fallback_pulse([], "2024-06-01", "2024-06-07")
        raw = f"```json\n{json.dumps(payload)}\n```"
        model = self._make_model(raw)
        result = _call_gemini(model, "test prompt")
        assert "top_themes" in result


# ── generate_pulse ─────────────────────────────────────────────────────────────


class TestGeneratePulse:
    def _make_gemini_mock(self) -> MagicMock:
        payload = _fallback_pulse([], "2024-06-01", "2024-06-07")
        mock_response = MagicMock()
        mock_response.text = json.dumps(payload)
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        return mock_model

    @patch("app.analysis.summarizer.genai")
    def test_returns_pulse_detail_instance(
        self, mock_genai: MagicMock, classified_reviews: list[dict]
    ):
        mock_genai.GenerativeModel.return_value = self._make_gemini_mock()
        mock_genai.configure = MagicMock()
        mock_genai.types.GenerationConfig = MagicMock()

        result = generate_pulse(classified_reviews, "2024-06-07", "2024-06-07", "run-001")
        assert isinstance(result, PulseDetail)

    @patch("app.analysis.summarizer.genai")
    def test_timeline_formatted_correctly(
        self,
        mock_genai: MagicMock,
        valid_pulse_json: str,
        classified_reviews: list[dict[str, Any]],
    ) -> None:
        """Timeline should be correctly formatted from YYYY-MM-DD input."""
        mock_gemini = MagicMock()
        mock_gemini.generate_content.return_value = MagicMock(text=valid_pulse_json)
        mock_genai.GenerativeModel.return_value = mock_gemini
        mock_genai.configure = MagicMock()
        mock_genai.types.GenerationConfig = MagicMock()

        result = generate_pulse(classified_reviews, "2024-06-01", "2024-06-07", "test-run")
        assert result.timeline == "01 Jun – 07 Jun '24"

    @patch("app.analysis.summarizer.genai")
    def test_total_reviews_matches_input(
        self, mock_genai: MagicMock, classified_reviews: list[dict]
    ):
        mock_genai.GenerativeModel.return_value = self._make_gemini_mock()
        mock_genai.configure = MagicMock()
        mock_genai.types.GenerationConfig = MagicMock()

        result = generate_pulse(classified_reviews, "2024-06-07", "2024-06-07", "run-001")
        assert result.total_reviews_analyzed == len(classified_reviews)

    @patch("app.analysis.summarizer.genai")
    def test_run_id_propagated(
        self, mock_genai: MagicMock, classified_reviews: list[dict]
    ):
        mock_genai.GenerativeModel.return_value = self._make_gemini_mock()
        mock_genai.configure = MagicMock()
        mock_genai.types.GenerationConfig = MagicMock()

        result = generate_pulse(classified_reviews, "2024-06-07", "2024-06-07", "run-XYZ")
        assert result.run_id == "run-XYZ"

    @patch("app.analysis.summarizer.genai")
    def test_output_word_count_under_250(
        self, mock_genai: MagicMock, classified_reviews: list[dict]
    ):
        mock_genai.GenerativeModel.return_value = self._make_gemini_mock()
        mock_genai.configure = MagicMock()
        mock_genai.types.GenerationConfig = MagicMock()

        result = generate_pulse(classified_reviews, "2024-06-07", "2024-06-07", "run-001")

        word_count = 0
        for theme in result.top_themes:
            word_count += len(theme.summary.split())
        for action in result.action_ideas:
            word_count += len(action.action.split())

        assert word_count <= 250, f"Word count {word_count} exceeds 250-word limit"

    @patch("app.analysis.summarizer.genai")
    def test_three_themes_three_quotes_three_actions(
        self, mock_genai: MagicMock, classified_reviews: list[dict]
    ):
        mock_genai.GenerativeModel.return_value = self._make_gemini_mock()
        mock_genai.configure = MagicMock()
        mock_genai.types.GenerationConfig = MagicMock()

        result = generate_pulse(classified_reviews, "2024-06-07", "2024-06-07", "run-001")
        assert len(result.top_themes) == 3
        assert len(result.verbatim_quotes) == 3
        assert len(result.action_ideas) == 3

    @patch("app.analysis.summarizer.genai")
    def test_missing_api_key_falls_back_gracefully(
        self, mock_genai: MagicMock, classified_reviews: list[dict], monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("GEMINI_API_KEY", "")
        from app.config import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        result = generate_pulse(classified_reviews, "2024-06-07", "2024-06-07", "run-001")
        assert isinstance(result, PulseDetail)
        get_settings.cache_clear()  # type: ignore[attr-defined]

    @patch("app.analysis.summarizer.genai")
    def test_invalid_end_date_format_handled(
        self, mock_genai: MagicMock, classified_reviews: list[dict]
    ):
        mock_genai.GenerativeModel.return_value = self._make_gemini_mock()
        mock_genai.configure = MagicMock()
        mock_genai.types.GenerationConfig = MagicMock()
        # Non-ISO date should not raise — falls back to raw string
        result = generate_pulse(classified_reviews, "not-a-date", "not-a-date-2", "test-run")
        assert result.timeline == "not-a-date to not-a-date-2"
