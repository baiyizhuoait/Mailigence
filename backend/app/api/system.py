"""System status endpoint — the dashboard's "it is alive" evidence.

One read-only call answers the stability questions a reviewer (or a user who
just opened the app) asks first:

* is the database reachable, and how slow is it?
* which backend version is running, and for how long?
* when did the last mailbox sync happen?
* are the real-time (IDLE) listeners healthy?
* did anything fail in the last 24 hours?

Everything here is derived from data the backend already owns; no extra
tables, no background work on the request path.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.config import settings
from app.database import get_db
from app.models.email_account import EmailAccount, SyncStatus
from app.models.import_job import ImportJob, ImportStatus
from app.services.ai_config import load_ai_config
from app.services.idle_manager import manager as idle_manager

router = APIRouter(prefix="/api/system", tags=["system"])

# Process start time (monotonic is immune to wall-clock changes).
_STARTED_AT = time.monotonic()


def _is_local_url(url: str) -> bool:
    """True when the AI endpoint is a local inference server.

    Used for the privacy badge: only a local base_url means mail content never
    leaves the machine.
    """
    u = (url or "").lower()
    return any(
        token in u
        for token in ("localhost", "127.0.0.1", "[::1]", "0.0.0.0")
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@router.get("/status")
async def system_status(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Aggregate health snapshot for the Settings ▸ System status panel."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    # ---- database round-trip ------------------------------------------------
    db_ok = True
    db_error = ""
    started = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - only when PG is down
        db_ok = False
        db_error = str(exc)[:200]
    db_latency_ms = round((time.perf_counter() - started) * 1000, 1)

    # ---- accounts / last sync ----------------------------------------------
    accounts = list(
        (
            await db.execute(
                select(
                    EmailAccount.id,
                    EmailAccount.sync_status,
                    EmailAccount.last_synced_at,
                    EmailAccount.last_error,
                )
            )
        ).all()
    )
    last_sync_at = max(
        (a.last_synced_at for a in accounts if a.last_synced_at), default=None
    )
    sync_errors = [
        {
            "kind": "sync",
            "account_id": a.id,
            "error": (a.last_error or "")[:160],
            "at": _iso(a.last_synced_at),
        }
        for a in accounts
        # Only errors that are still recent; a stale failure from last week is
        # history, not a current outage.
        if a.sync_status == SyncStatus.ERROR
        and (a.last_synced_at is None or a.last_synced_at >= cutoff)
    ]

    # ---- IDLE listeners -----------------------------------------------------
    idle_states = idle_manager.get_all_status()
    idle_running = sum(1 for st in idle_states.values() if st.get("running"))
    idle_polling_only = sum(
        1 for st in idle_states.values() if st.get("error") == "polling_only"
    )
    idle_errors = sum(
        1
        for st in idle_states.values()
        if st.get("running") and (st.get("error") or "")
    )
    idle_last_event = max(
        (st.get("last_event_at") for st in idle_states.values() if st.get("last_event_at")),
        default=None,
    )

    # ---- failures in the last 24h -----------------------------------------
    failed_jobs = list(
        (
            await db.execute(
                select(ImportJob)
                .where(
                    ImportJob.status == ImportStatus.FAILED,
                    func.coalesce(ImportJob.finished_at, ImportJob.created_at) >= cutoff,
                )
                .order_by(func.coalesce(ImportJob.finished_at, ImportJob.created_at).desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    failed_items = [
        {
            "kind": "import",
            "id": job.id,
            "account_id": job.account_id,
            "error": (job.error or "")[:160],
            "at": _iso(job.finished_at or job.created_at),
        }
        for job in failed_jobs
    ]

    # ---- active AI configuration (privacy / local-model badge) -------------
    cfg = await load_ai_config(db)
    ai = {
        "mode": cfg.effective_mode,
        "configured": cfg.use_ai,
        "provider": cfg.provider,
        "model": cfg.model,
        "local": _is_local_url(cfg.base_url),
    }

    healthy = db_ok and not failed_jobs and not sync_errors
    return {
        "status": "ok" if healthy else "degraded",
        "version": __version__,
        "demo_mode": settings.demo_mode,
        "uptime_seconds": int(time.monotonic() - _STARTED_AT),
        "database": {
            "ok": db_ok,
            "latency_ms": db_latency_ms,
            "error": db_error,
        },
        "accounts": {
            "total": len(accounts),
            "sync_errors": len(sync_errors),
        },
        "last_sync_at": _iso(last_sync_at),
        "idle": {
            "running": idle_running,
            "polling_only": idle_polling_only,
            "errors": idle_errors,
            "last_event_at": idle_last_event,
        },
        "failed_24h": {
            "import_jobs": len(failed_jobs),
            "sync_errors": len(sync_errors),
            "items": (failed_items + sync_errors)[:10],
        },
        "ai": ai,
    }
