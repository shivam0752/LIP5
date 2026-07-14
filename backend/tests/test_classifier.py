"""
test_classifier.py — Unit tests for the Gemini classification pipeline.

All Gemini API calls are mocked. Tests verify:
  - Domain mapping logic (validate_domain)
  - Batch processing structure
  - Fallback to "Other" on Gemini errors
  - classify_reviews enriches reviews with domain + confidence
  - Missing GEMINI_API_KEY raises ValueError
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.analysis.classifier import (
    DOMAINS,
    _classify_batch,
    _validate_domain,
    classify_reviews,
)


# ── _validate_domain ───────────────────────────────────────────────────────────


class TestValidateDomain:
    @pytest.mark.parametrize("domain", DOMAINS)
    def test_exact_match_returns_domain(self, domain: str):
        assert _validate_domain(domain) == domain

    @pytest.mark.parametrize("domain", DOMAINS)
    def test_lowercase_input_matches(self, domain: str):
        assert _validate_domain(domain.lower()) == domain

    @pytest.mark.parametrize("domain", DOMAINS)
    def test_uppercase_input_matches(self, domain: str):
        assert _validate_domain(domain.upper()) == domain

    def test_unknown_domain_returns_other(self):
        assert _validate_domain("Completely Unknown Domain") == "Other"

    def test_partial_match_payments(self):
        # "Payments" is the left side of "Payments & Funding" so it fuzzy-matches
        result = _validate_domain("Payments issue with UPI")
        assert result == "Payments & Funding"

    def test_partial_match_kyc(self):
        # "KYC" is the left side of "KYC & Onboarding"
        result = _validate_domain("KYC verification stuck")
        assert result == "KYC & Onboarding"

    def test_empty_string_returns_other(self):
        assert _validate_domain("") == "Other"


# ── _classify_batch (mocked Gemini) ───────────────────────────────────────────


class TestClassifyBatch:
    def _make_model(self, json_text: str) -> MagicMock:
        mock_response = MagicMock()
        mock_response.text = json_text
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        return mock_model

    def test_valid_response_parsed_correctly(self):
        batch = [
            {"id": 0, "rating": 1, "review_title": "Crash", "review_text": "App crashes at market open."},
            {"id": 1, "rating": 2, "review_title": "UPI", "review_text": "UPI payment failed repeatedly."},
        ]
        json_text = (
            '[{"id": 0, "domain": "App Stability & UI", "confidence": "high"},'
            '{"id": 1, "domain": "Payments & Funding", "confidence": "medium"}]'
        )
        model = self._make_model(json_text)
        result = _classify_batch(model, batch)

        assert result[0]["domain"] == "App Stability & UI"
        assert result[0]["confidence"] == "high"
        assert result[1]["domain"] == "Payments & Funding"
        assert result[1]["confidence"] == "medium"

    def test_markdown_fence_stripped(self):
        batch = [{"id": 0, "rating": 3, "review_title": "OK", "review_text": "App is okay but slow."}]
        json_text = '```json\n[{"id": 0, "domain": "App Stability & UI", "confidence": "low"}]\n```'
        model = self._make_model(json_text)
        result = _classify_batch(model, batch)
        assert result[0]["domain"] == "App Stability & UI"

    def test_gemini_error_falls_back_to_other(self):
        batch = [{"id": 0, "rating": 1, "review_title": "Bad", "review_text": "This app is terrible always."}]
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = RuntimeError("Network error")
        result = _classify_batch(mock_model, batch)
        assert result[0]["domain"] == "Other"
        assert result[0]["confidence"] == "medium"

    def test_invalid_json_falls_back_to_other(self):
        batch = [{"id": 0, "rating": 2, "review_title": "Meh", "review_text": "Not great but acceptable overall."}]
        model = self._make_model("not valid json at all!!!")
        result = _classify_batch(model, batch)
        assert result[0]["domain"] == "Other"
        assert result[0]["confidence"] == "medium"

    def test_unknown_domain_in_response_normalised(self):
        batch = [{"id": 0, "rating": 3, "review_title": "x", "review_text": "Something completely random here."}]
        json_text = '[{"id": 0, "domain": "Totally Made Up Domain XYZ", "confidence": "high"}]'
        model = self._make_model(json_text)
        result = _classify_batch(model, batch)
        assert result[0]["domain"] == "Other"


# ── classify_reviews ───────────────────────────────────────────────────────────


class TestClassifyReviews:
    def _gemini_side_effect(self, reviews: list[dict], *args, **kwargs) -> list[dict]:
        """Simulate Gemini returning domain based on review index."""
        mock_domains = [
            "App Stability & UI",
            "Payments & Funding",
            "App Stability & UI",
            "KYC & Onboarding",
            "Customer Support Quality",
        ]
        return [
            {"id": r["id"], "domain": mock_domains[r["id"] % len(mock_domains)], "confidence": "high"}
            for r in reviews
        ]

    @patch("app.analysis.classifier.genai")
    def test_enriched_reviews_have_domain_and_confidence(
        self, mock_genai: MagicMock, sample_reviews: list[dict]
    ):
        # Build JSON response for all 5 reviews
        response_json = "[" + ",".join(
            f'{{"id": {i}, "domain": "App Stability & UI", "confidence": "high"}}'
            for i in range(len(sample_reviews))
        ) + "]"

        mock_response = MagicMock()
        mock_response.text = response_json
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = MagicMock()
        mock_genai.types.GenerationConfig = MagicMock()

        result = classify_reviews(sample_reviews)

        assert len(result) == len(sample_reviews)
        for item in result:
            assert "domain" in item
            assert "confidence" in item
            assert "id" in item

    @patch("app.analysis.classifier.genai")
    def test_missing_api_key_falls_back_gracefully(self, mock_genai: MagicMock, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GEMINI_API_KEY", "")
        from app.config import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        result = classify_reviews([{"rating": 1, "review_title": "crash", "review_text": "app crashes constantly."}])
        assert len(result) == 1
        assert result[0]["domain"] == "App Stability & UI"
        assert result[0]["confidence"] == "medium"
        get_settings.cache_clear()  # type: ignore[attr-defined]

    @patch("app.analysis.classifier.genai")
    def test_empty_reviews_returns_empty(self, mock_genai: MagicMock):
        mock_genai.GenerativeModel.return_value = MagicMock()
        mock_genai.configure = MagicMock()
        result = classify_reviews([])
        assert result == []

    @patch("app.analysis.classifier.genai")
    def test_gemini_failure_falls_back_to_heuristic(
        self, mock_genai: MagicMock, sample_reviews: list[dict]
    ):
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = RuntimeError("Quota exceeded")
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = MagicMock()
        mock_genai.types.GenerationConfig = MagicMock()

        result = classify_reviews(sample_reviews)
        assert len(result) == len(sample_reviews)
        for item in result:
            assert "domain" in item
            assert item["confidence"] == "medium"
