"""
main.py — FastAPI application entry point with CORS, lifespan, and router mount.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.storage.store import append_log


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    # Ensure all data directories exist
    settings.ensure_dirs()
    append_log("LIP5 backend starting up…")

    # Start the weekly scheduler
    from app.scheduler import scheduler  # noqa: PLC0415
    scheduler.start()
    append_log("APScheduler started (weekly pulse cron active).")

    yield  # ── server is live ──────────────────────────────────────────────────

    scheduler.shutdown(wait=False)
    append_log("LIP5 backend shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="LIP5 — Automated App Store Pulse API",
        description=(
            "Ingests Groww app-store reviews weekly, classifies with Gemini, "
            "generates a Google Doc executive pulse, and stages a Gmail draft."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
