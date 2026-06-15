"""
scheduler.py — APScheduler weekly cron: fires every Sunday at 00:00 UTC.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.storage.store import append_log, new_run_id, reset_run_state


def _build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _weekly_run,
        trigger=CronTrigger(day_of_week="sun", hour=0, minute=0, timezone="UTC"),
        id="weekly_pulse",
        name="Weekly Groww App Pulse",
        replace_existing=True,
    )
    return scheduler


async def _weekly_run() -> None:
    """
    Compute the previous Mon–Sun window and kick off the pipeline.
    Imported here to avoid circular import at startup.
    """
    from app.api.routes import _run_pipeline  # noqa: PLC0415

    end = datetime.utcnow().date()
    start = end - timedelta(days=6)
    run_id = new_run_id()
    reset_run_state(run_id)
    append_log(
        f"Scheduled weekly run started for {start} → {end}",
        run_id=run_id,
    )
    await _run_pipeline(run_id, str(start), str(end))


scheduler = _build_scheduler()
