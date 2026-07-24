"""
Insight API — trend analysis with meal-type distribution + 7-day AI suggestions.
"""
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.ai_trend import get_daily_trend, update_trend_cache
from app.services.ai_suggestion import generate_7day_suggestions, get_suggestion_history

router = APIRouter(prefix="/api/v1/insight", tags=["insight"])


@router.get("/trend")
async def trend_analysis(
    period: str = Query("weekly", pattern="^(weekly|monthly)$"),
    user_id: str = Query("anonymous"),
    db: AsyncSession = Depends(get_db),
):
    """Get trend data with meal-type distribution for weekly or monthly period."""
    days = 7 if period == "weekly" else 30
    trend = await get_daily_trend(user_id=user_id, days=days, db=db)
    return {"status": "ok", "period": period, "days": trend}


@router.get("/suggestions")
async def insight_suggestions(
    user_id: str = Query("anonymous"),
    db: AsyncSession = Depends(get_db),
):
    """Generate 7-day AI dietary suggestions."""
    suggestions = await generate_7day_suggestions(user_id=user_id, db=db)
    return {"status": "ok", "suggestions": suggestions}


@router.get("/history")
async def suggestion_history(
    user_id: str = Query("anonymous"),
    days: int = Query(7),
    db: AsyncSession = Depends(get_db),
):
    """Get recent AI suggestion history."""
    history = await get_suggestion_history(user_id=user_id, days=days, db=db)
    return {"status": "ok", "count": len(history), "history": history}


@router.post("/refresh-cache")
async def refresh_trend_cache(
    user_id: str = Query("anonymous"),
    db: AsyncSession = Depends(get_db),
):
    """Manually refresh trend cache for today."""
    await update_trend_cache(user_id=user_id, db=db)
    return {"status": "ok", "message": "Trend cache updated"}
