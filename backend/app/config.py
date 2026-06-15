"""
config.py — pydantic-settings environment configuration with derived path helpers.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Gemini ─────────────────────────────────────────────────────────────────
    gemini_api_key: str = ""

    # ── Google OAuth ───────────────────────────────────────────────────────────
    google_client_secrets_file: str = "./credentials.json"
    google_client_secrets_json: str = ""
    google_token_json: str = ""

    # ── App Store ──────────────────────────────────────────────────────────────
    groww_package_name: str = "com.nextbillion.groww"

    # ── CORS ───────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Storage ────────────────────────────────────────────────────────────────
    data_dir: str = "./data"

    # ── Derived helpers ────────────────────────────────────────────────────────
    @property
    def data_path(self) -> Path:
        return Path(self.data_dir).resolve()

    @property
    def reviews_path(self) -> Path:
        return self.data_path / "reviews"

    @property
    def pulses_path(self) -> Path:
        return self.data_path / "pulses"

    @property
    def logs_path(self) -> Path:
        return self.data_path / "logs.jsonl"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        """Create all required data subdirectories if absent."""
        self.reviews_path.mkdir(parents=True, exist_ok=True)
        self.pulses_path.mkdir(parents=True, exist_ok=True)
        # Ensure logs.jsonl file directory exists
        self.logs_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
