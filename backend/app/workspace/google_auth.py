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

import json
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
    Load credentials from:
    1. GOOGLE_TOKEN_JSON environment variable if set.
    2. Local token.json file path otherwise.

    Refreshes the credentials if they are expired.
    Raises RuntimeError if no valid token is found or if refresh fails.
    """
    settings = get_settings()
    creds: Credentials | None = None

    # 1. Try to load from GOOGLE_TOKEN_JSON environment variable
    if settings.google_token_json:
        try:
            info = json.loads(settings.google_token_json)
            creds = Credentials.from_authorized_user_info(info, SCOPES)
            logger.info("Loaded Google OAuth credentials from GOOGLE_TOKEN_JSON environment variable.")
        except Exception as exc:
            logger.warning("Could not load credentials from GOOGLE_TOKEN_JSON: %s", exc)
            creds = None

    # 2. Try to load from local file
    if not creds:
        token_file = _token_path()
        if token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
                logger.info("Loaded Google OAuth credentials from local file: %s", token_file)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not load token.json: %s. Will re-authenticate.", exc)
                creds = None

    if creds:
        if creds.valid:
            return creds

        if creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Google OAuth token…")
            try:
                creds.refresh(Request())
                _save_token(creds, _token_path())
                return creds
            except Exception as exc:
                logger.error("Failed to refresh Google OAuth token: %s", exc)

    raise RuntimeError(
        "No valid Google OAuth token found. "
        "Either set the GOOGLE_TOKEN_JSON environment variable with your token JSON, "
        "or run 'python -m app.workspace.google_auth' locally to complete the OAuth flow and generate a token."
    )


def _save_token(creds: Credentials, token_file: Path) -> None:
    """Persist credentials to token.json if possible."""
    try:
        token_file.write_text(creds.to_json(), encoding="utf-8")
        logger.info("OAuth token saved to %s", token_file)
    except Exception as exc:
        logger.warning(
            "Could not save token to %s: %s. Proceeding with refreshed token in-memory.",
            token_file,
            exc,
        )


# ── CLI entry point ─────────────────────────────────────────────────────────────

def run_oauth_flow() -> None:
    """Interactive OAuth2 flow — run locally to generate token.json."""
    settings = get_settings()
    client_config = None

    # Try loading client config from GOOGLE_CLIENT_SECRETS_JSON first
    if settings.google_client_secrets_json:
        try:
            client_config = json.loads(settings.google_client_secrets_json)
            print("Loaded Google client secrets from GOOGLE_CLIENT_SECRETS_JSON environment variable.")
        except Exception as exc:
            print(f"ERROR: Could not parse GOOGLE_CLIENT_SECRETS_JSON: {exc}")
            return

    # Fall back to file
    if not client_config:
        creds_file = Path(settings.google_client_secrets_file).resolve()
        if not creds_file.exists():
            print(f"ERROR: Google client secrets not found at '{creds_file}' and GOOGLE_CLIENT_SECRETS_JSON is not set.")
            print("Download credentials.json from Google Cloud Console > APIs & Services > Credentials.")
            return
        try:
            with open(creds_file, "r", encoding="utf-8") as f:
                client_config = json.load(f)
        except Exception as exc:
            print(f"ERROR: Could not read/parse client secrets file: {exc}")
            return

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)

    token_file = _token_path()
    _save_token(creds, token_file)
    print(f"\n✅ OAuth token saved to: {token_file}")
    print("You can copy the contents of this file and set it as the GOOGLE_TOKEN_JSON environment variable.")


if __name__ == "__main__":
    run_oauth_flow()
