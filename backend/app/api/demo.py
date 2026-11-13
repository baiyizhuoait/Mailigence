"""Demo-mode helpers for the public / trial instance.

Only meaningful when ``DEMO_MODE=1``. The reset endpoint lets a visitor undo
whatever they clicked (handled mails, chat history side effects) without
touching a database console — useful when several reviewers share one instance.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.demo_data import reset_demo_data

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/status")
async def demo_status() -> dict:
    """Always answers 200 so the UI can hide demo affordances in normal builds."""
    return {"demo_mode": settings.demo_mode}


@router.post("/reset")
async def demo_reset(db: AsyncSession = Depends(get_db)) -> dict:
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Demo mode is not enabled")
    accounts = await reset_demo_data(db)
    return {"reset": True, "accounts": accounts}
