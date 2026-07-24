"""
Ads API — log ad impressions and clicks for free-tier monetization.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.billing import AdLog

router = APIRouter(prefix="/api/v1/ads", tags=["ads"])


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@router.post("/log")
async def log_ad():
    """Log an ad impression or click event — 已临时禁用 (2026-07-24)."""
    raise HTTPException(
        status_code=501,
        detail={"status": "disabled", "message": "Ad logging temporarily disabled"},
    )


@router.get("/stats")
async def ad_stats():
    """Get aggregate ad performance stats — 已临时禁用 (2026-07-24)."""
    raise HTTPException(
        status_code=501,
        detail={"status": "disabled", "message": "Ad stats temporarily disabled"},
    )
