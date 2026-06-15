"""
google_auth.py — OAuth2 flow with token.json caching and silent refresh.

Usage (first-time local setup):
    python -m app.workspace.google_auth

This opens a browser, completes the OAuth2 consent flow, and writes token.json.
On subsequent calls, build_credentials() silently refreshes the token if needed.

Required OAuth Scopes:
    https://www.googleapis.com/auth/documents
    https://www.googleapis.com/auth/gmail.compose
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from app.config import get_settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.compose",
]

_TOKEN_FILENAME = "token.json"


def _token_path() -> Path:
    """Resolve the token.json path relative to the credentials file location."""
    settings = get_settings()
    creds_path = Path(settings.google_client_secrets_file).resolve()
    return creds_path.parent / _TOKEN_FILENAME


def build_credentials() -> Credentials:
    """
    Load credentials from token.json, refreshing if expired.
    Raises FileNotFoundError if credentials.json is missing.
    Raises RuntimeError if no token exists (run the CLI first).
    """
    settings = get_settings()
    creds_file = Path(settings.google_client_secrets_file).resolve()

    if not creds_file.exists():
        raise FileNotFoundError(
            f"Google client secrets not found at '{creds_file}'. "
            "Download credentials.json from Google Cloud Console and set "
            "GOOGLE_CLIENT_SECRETS_FILE in your .env file."
        )

    token_file = _token_path()
    creds: Credentials | None = None

    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load token.json: %s. Will re-authenticate.", exc)
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        logger.info("Refreshing expired Google OAuth token…")
        creds.refresh(Request())
        _save_token(creds, token_file)
        return creds

    raise RuntimeError(
        "No valid Google OAuth token found. "
        "Run 'python -m app.workspace.google_auth' locally to complete the OAuth flow."
    )


def _save_token(creds: Credentials, token_file: Path) -> None:
    """Persist credentials to token.json."""
    token_file.write_text(creds.to_json(), encoding="utf-8")
    logger.info("OAuth token saved to %s", token_file)


# ── CLI entry point ─────────────────────────────────────────────────────────────

def run_oauth_flow() -> None:
    """Interactive OAuth2 flow — run locally to generate token.json."""
    settings = get_settings()
    creds_file = Path(settings.google_client_secrets_file).resolve()

    if not creds_file.exists():
        print(f"ERROR: credentials.json not found at '{creds_file}'.")
        print("Download it from Google Cloud Console > APIs & Services > Credentials.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
    creds = flow.run_local_server(port=0)

    token_file = _token_path()
    _save_token(creds, token_file)
    print(f"\n✅ OAuth token saved to: {token_file}")
    print("You can now mount this file as a Railway secret file for production.")


if __name__ == "__main__":
    run_oauth_flow()
