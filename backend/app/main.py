"""FastAPI application entry point.

Run (dev):
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import logging
import time
import traceback
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select

from app.api import (
    accounts,
    ads,
    categories,
    chat,
    dashboard,
    demo,
    emails,
    idle,
    import_jobs,
    memories,
    oauth,
    replies,
    reports,
    search,
    system,
)
from app.api.settings import router as settings_router
from app.config import settings
from app.database import SessionLocal, init_db
from app.models.email_account import EmailAccount
from app.services import http_client, mail_sync, reconcile_orphans
from app.services.demo_data import seed_demo_data
from app.services.idle_manager import manager as idle_manager

_log = logging.getLogger(__name__)

# Background sync interval for servers that don't support IMAP IDLE
# (including Microsoft Graph OAuth accounts, which have no IMAP scope).
BACKGROUND_SYNC_SECONDS = 60
# How often to sweep for emails still waiting on AI analysis (new imports that
# exceeded one batch, or mails left uncategorized by a category delete). Kept
# short so fresh mail reaches the dashboard in seconds, not minutes.
ANALYSIS_SWEEP_SECONDS = 15


async def _analysis_sweep_loop() -> None:
    """Periodically find emails that need AI analysis and run it.

    ``run_analysis`` processes up to ANALYSIS_BATCH mails per run, so a large
    import can leave a backlog; this loop keeps working the queue every few
    seconds until it is empty. It also covers mails whose category was deleted
    (their ``category`` is NULL, which the analysis query treats as pending).
    """
    await asyncio.sleep(5)  # let startup settle
    while True:
        try:
            async with SessionLocal() as db:
                from app.services.analysis_service import pending_count
                pending = await pending_count(db)
            if pending > 0:
                from app.services.analysis_service import manager as analysis_mgr
                analysis_mgr.start(None)
        except Exception as exc:
            _log.error("Analysis sweep error: %s", exc)
        await asyncio.sleep(ANALYSIS_SWEEP_SECONDS)


async def _embedding_sweep_loop() -> None:
    """Periodically embed mails that still lack a vector (semantic search).

    Mirrors the analysis sweep: new imports / syncs produce mails whose
    ``embedding`` column is NULL; this loop keeps the backlog working in the
    background so the search UI can gradually gain semantic recall.
    """
    await asyncio.sleep(5)  # let startup settle
    while True:
        try:
            from app.services.embedding_service import manager as emb_mgr
            from app.services.embedding_service import pending_embedding_count

            async with SessionLocal() as db:
                pending = await pending_embedding_count(db)
            if pending > 0:
                emb_mgr.start()
        except Exception as exc:
            _log.error("Embedding sweep error: %s", exc)
        await asyncio.sleep(ANALYSIS_SWEEP_SECONDS)


# An IDLE loop counts as "fresh" — i.e. the background poller may skip the
# account — only if it synced successfully this recently. Anything older
# (IDLE silently stuck, erroring, or never synced) falls back to polling.
IDLE_FRESH_MINUTES = 10


def _idle_loop_is_fresh(status: dict, now: datetime) -> bool:
    if not status.get("running") or status.get("error"):
        return False
    last_sync = status.get("last_sync_at")
    if not last_sync:
        return False
    try:
        age = (now - datetime.fromisoformat(last_sync)).total_seconds()
    except (TypeError, ValueError):
        return False
    return 0 <= age < IDLE_FRESH_MINUTES * 60


async def _background_sync_loop() -> None:
    """Periodically sync all accounts as a fallback for non-IDLE servers.

    Skips an account only when its IDLE loop is running, error-free, and has
    demonstrably synced within ``IDLE_FRESH_MINUTES`` (stamped by the IDLE
    manager on every successful sync pass). The old check (``running and no
    error``) trusted an IDLE connection that could sit idle-spinning forever
    without ever syncing, leaving mail un-fetched for unbounded time.
    """
    await asyncio.sleep(10)  # let startup settle
    while True:
        try:
            async with SessionLocal() as db:
                result = await db.execute(select(EmailAccount))
                acct_list = list(result.scalars().all())
                since = date.today() - timedelta(days=1)
                now = datetime.now(timezone.utc)
                for acct in acct_list:
                    if _idle_loop_is_fresh(idle_manager.get_status(acct.id), now):
                        continue
                    try:
                        count = await mail_sync.sync_account(db, acct, since=since)
                        if count > 0:
                            from app.services.analysis_service import manager as analysis_mgr
                            analysis_mgr.start(acct.id)
                            from app.services.embedding_service import manager as emb_mgr
                            emb_mgr.start()
                    except Exception as exc:
                        # Don't crash the loop, but surface the failure in the
                        # logs instead of silently swallowing it.
                        _log.warning(
                            "Background sync failed for account %s: %s",
                            acct.email, exc,
                        )
        except Exception as exc:
            _log.error("Background sync loop error: %s", exc)
        await asyncio.sleep(BACKGROUND_SYNC_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on first start (Stage 1 convenience; use Alembic later).
    try:
        await init_db()
    except Exception as exc:
        _log.error(
            "Database connection failed: %s\n"
            "Please make sure PostgreSQL is running and that DATABASE_URL in "
            "backend/.env is correct (see backend/.env.example).",
            exc,
        )
        # Fail fast with a clear message instead of an opaque traceback.
        raise SystemExit(1) from exc
    # Mark any import jobs orphaned by a crash/restart as failed so the UI
    # never shows a permanently "running" job.
    async with SessionLocal() as db:
        await reconcile_orphans(db)
        if settings.demo_mode:
            # Seeded once; the demo router's /reset endpoint re-seeds on demand.
            created = await seed_demo_data(db)
            if created:
                _log.info("Demo mode: seeded %s demo mailboxes", created)
        else:
            # Auto-start IDLE monitoring for all existing accounts so new mail
            # is pushed in real-time without manual intervention.
            result = await db.execute(select(EmailAccount))
            for acct in result.scalars().all():
                await idle_manager.start(acct.id)
    if settings.demo_mode:
        # Demo mailboxes are fake and point at demo.invalid: every loop below
        # would either fail against a non-existent server or burn model calls.
        # The dataset is already analysed, so nothing needs a background pass.
        _log.info("Demo mode: background sync / analysis / embedding loops disabled")
        sync_task = analysis_task = embedding_task = None
    else:
        # Start background sync as a fallback for servers without IDLE support.
        sync_task = asyncio.create_task(_background_sync_loop())
        # Start the analysis sweep so unanalyzed/uncategorized mail is always
        # picked up automatically.
        analysis_task = asyncio.create_task(_analysis_sweep_loop())
        # Start the embedding backfill sweep (semantic search vectors).
        embedding_task = asyncio.create_task(_embedding_sweep_loop())
    yield
    # Stop all IDLE listeners on shutdown.
    idle_manager.stop_all()
    for task in (sync_task, analysis_task, embedding_task):
        if task is not None:
            task.cancel()
    # Close the shared HTTP client's keep-alive connection pool.
    await http_client.aclose()


app = FastAPI(
    title="Mailigence API",
    version="0.2.0",
    description="Multi-platform email aggregation & analysis backend (Stage 2).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- demo guard ------------------------------------------------------------
# Demo instances are reachable by people who are not the owner, so they get two
# extra rules that normal instances never see:
#  * an optional shared-secret gate (DEMO_ACCESS_TOKEN) for a public tunnel,
#  * a write block on the paths that would store real credentials or try to
#    reach a real mail server — those would either leak or corrupt the demo.
_DEMO_BLOCKED_PREFIXES = (
    "/api/accounts",
    "/api/oauth",
    "/api/import-jobs",
    "/api/dashboard/sync",
    # One visitor saving "rules_only" or a bogus provider profile would shadow
    # the demo's own key and break AI chat for everyone else.
    "/api/settings",
)
_DEMO_COOKIE = "mailigence_demo"

# ---- demo AI budget ---------------------------------------------------------
# The demo instance may hold a real provider key so the AI chat/draft features
# are actually demonstrable. That key must not be burned by a public visitor,
# so every demo AI request is counted: per visitor per hour and per instance
# per day. Counters live in memory on purpose — a demo instance is a single
# process and a restart resetting the budget is acceptable.
_DEMO_AI_HOURLY: dict[str, list[float]] = {}
_DEMO_AI_DAILY: dict[str, object] = {"day": "", "count": 0}


def _demo_is_ai_request(request: Request) -> bool:
    """Only the endpoints that actually spend model tokens."""
    if request.method != "POST":
        return False
    path = request.url.path
    if path.startswith("/api/chat"):
        return True
    if path == "/api/ai/memories":
        return True
    return path.startswith("/api/emails/") and path.endswith("/draft-replies")


def _demo_visitor_ip(request: Request) -> str:
    """Visitor identity behind a tunnel (Cloudflare / generic proxy header)."""
    for header in ("cf-connecting-ip", "x-forwarded-for"):
        value = request.headers.get(header, "").split(",")[0].strip()
        if value:
            return value
    return request.client.host if request.client else "unknown"


def _demo_ai_budget_exhausted(request: Request) -> str | None:
    """Consume one AI credit; return a message when the budget is gone."""
    daily_cap = settings.demo_ai_daily_limit
    hourly_cap = settings.demo_ai_ip_hourly_limit
    if daily_cap <= 0 and hourly_cap <= 0:
        return None

    now = time.time()
    today = date.today().isoformat()
    if _DEMO_AI_DAILY["day"] != today:
        _DEMO_AI_DAILY["day"] = today
        _DEMO_AI_DAILY["count"] = 0
    used_today = int(_DEMO_AI_DAILY["count"])

    ip = _demo_visitor_ip(request)
    hour_hits = [t for t in _DEMO_AI_HOURLY.get(ip, []) if now - t < 3600]
    # Drop visitors whose window has expired so the map cannot grow forever.
    if len(_DEMO_AI_HOURLY) > 256:
        _DEMO_AI_HOURLY.clear()
        _DEMO_AI_HOURLY[ip] = hour_hits

    if hourly_cap > 0 and len(hour_hits) >= hourly_cap:
        _DEMO_AI_HOURLY[ip] = hour_hits
        return "AI 问答的每人每小时演示额度已用完，请一小时后再试。"
    if daily_cap > 0 and used_today >= daily_cap:
        _DEMO_AI_HOURLY[ip] = hour_hits
        return "演示环境的 AI 问答今日总额度已用完，请明天再试。"

    hour_hits.append(now)
    _DEMO_AI_HOURLY[ip] = hour_hits
    _DEMO_AI_DAILY["count"] = used_today + 1
    return None


_DEMO_GATE_FORM = """<!doctype html>
<meta charset="utf-8"><title>Mailigence Demo</title>
<body style="font-family:system-ui;display:grid;place-items:center;height:100vh;margin:0;background:#0f1115;color:#e6e8eb">
<form method="get" style="background:#171a21;padding:32px;border-radius:14px;border:1px solid #2a2f3a">
  <h2 style="margin:0 0 6px">Mailigence Demo</h2>
  <p style="margin:0 0 18px;color:#9aa0aa;font-size:14px">请输入访问口令</p>
  <input name="token" autofocus placeholder="Access token"
         style="padding:10px 12px;border-radius:8px;border:1px solid #2f3542;background:#0f1115;color:#e6e8eb;width:240px">
  <button style="margin-left:8px;padding:10px 16px;border-radius:8px;border:0;background:#4a9eff;color:#fff">进入</button>
</form>
"""


@app.middleware("http")
async def demo_guard(request: Request, call_next):
    if not settings.demo_mode:
        return await call_next(request)

    # Health is used by launchers / tunnels and exposes no mail data.
    if request.url.path == "/api/health":
        return await call_next(request)

    token = settings.demo_access_token
    if token:
        supplied = request.query_params.get("token") or request.cookies.get(_DEMO_COOKIE)
        if supplied != token:
            if request.url.path.startswith("/api/"):
                return JSONResponse(
                    {"detail": "Demo access token required"}, status_code=401
                )
            return HTMLResponse(_DEMO_GATE_FORM, status_code=401)
        if request.query_params.get("token"):
            response = await call_next(request)
            # 7 days: long enough for a reviewer session, short enough to expire.
            response.set_cookie(
                _DEMO_COOKIE, token, httponly=True, samesite="lax", max_age=604800
            )
            return response

    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and (
        request.url.path.startswith(_DEMO_BLOCKED_PREFIXES)
        # Sending a reply would hit a non-existent SMTP server; refuse it with a
        # clear reason instead of surfacing a confusing 502.
        or (
            request.url.path.startswith("/api/emails/")
            and request.url.path.endswith("/send-reply")
        )
    ):
        return JSONResponse(
            {
                "detail": (
                    "This action is disabled in demo mode: the demo dataset is "
                    "read-only and cannot connect to real mailboxes."
                )
            },
            status_code=403,
        )

    # Budget the few endpoints that spend the demo's own model credits.
    if _demo_is_ai_request(request):
        reason = _demo_ai_budget_exhausted(request)
        if reason:
            return JSONResponse({"detail": reason}, status_code=429)

    return await call_next(request)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "encryption_configured": settings.encryption_key_configured,
        "oauth_google_configured": bool(settings.google_oauth_client_id),
        "oauth_microsoft_configured": bool(settings.microsoft_oauth_client_id),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return a readable error body instead of a bare 500, and log the traceback.

    Without this handler, FastAPI returns ``Internal Server Error`` with no
    detail, so the frontend can't surface why a request failed.
    """
    tb = traceback.format_exc()
    _log.error(
        "Unhandled error on %s %s: %s\n%s",
        request.method,
        request.url.path,
        exc,
        tb,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(accounts.router)
app.include_router(oauth.router)
app.include_router(demo.router)
app.include_router(emails.router)
app.include_router(categories.router)
app.include_router(import_jobs.router)
app.include_router(dashboard.router)
app.include_router(ads.router)
app.include_router(ads.blocked_senders_router)
app.include_router(reports.router)
app.include_router(replies.router)
app.include_router(idle.router)
app.include_router(settings_router)
app.include_router(memories.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(system.router)
