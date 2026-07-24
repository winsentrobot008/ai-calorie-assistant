"""
Stats API — daily nutrition summary, trends & AI suggestions.
"""
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.meal import Meal
from app.models.user import User
from app.services.suggestion import generate_suggestions_safe

router = APIRouter(prefix="/api/v1", tags=["stats"])


async def _query_daily_stats(user_id: str, date_str: str, db: AsyncSession) -> dict:
    """Internal: query daily nutrition + goals for a user on a given date."""
    if not date_str:
        date_str = date.today().isoformat()

    try:
        day_start = datetime.strptime(date_str, "%Y-%m-%d")
        day_end = day_start.replace(hour=23, minute=59, second=59)
    except ValueError:
        return {"status": "error", "message": "Invalid date format, use YYYY-MM-DD"}

    # Sum nutrition from meals on that day
    query = select(
        func.coalesce(func.sum(Meal.calories), 0).label("total_calories"),
        func.coalesce(func.sum(Meal.protein_g), 0).label("total_protein"),
        func.coalesce(func.sum(Meal.fat_g), 0).label("total_fat"),
        func.coalesce(func.sum(Meal.carbs_g), 0).label("total_carbs"),
        func.count(Meal.id).label("meal_count"),
    ).where(
        Meal.user_id == user_id,
        Meal.created_at >= day_start,
        Meal.created_at <= day_end,
    )
    result = await db.execute(query)
    row = result.one()

    # Get user goals
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if user:
        goals = {
            "goal_type": user.goal_type,
            "daily_calories": user.daily_calories,
            "daily_protein": user.daily_protein,
            "daily_fat": user.daily_fat,
            "daily_carbs": user.daily_carbs,
        }
    else:
        goals = {
            "goal_type": "maintain",
            "daily_calories": 2000,
            "daily_protein": 60,
            "daily_fat": 65,
            "daily_carbs": 300,
        }

    return {
        "status": "ok",
        "date": date_str,
        "stats": {
            "calories": round(row.total_calories, 1),
            "protein_g": round(row.total_protein, 1),
            "fat_g": round(row.total_fat, 1),
            "carbs_g": round(row.total_carbs, 1),
            "meal_count": row.meal_count,
        },
        "goals": goals,
    }


@router.get("/stats/daily")
async def daily_stats(
    user_id: str = Query("anonymous"),
    date_str: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """Get daily nutrition summary for a user."""
    return await _query_daily_stats(user_id=user_id, date_str=date_str, db=db)


@router.get("/stats/suggestions")
async def get_suggestions(
    user_id: str = Query("anonymous"),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI dietary suggestions based on today's intake."""
    today_str = date.today().isoformat()
    stats_resp = await _query_daily_stats(user_id=user_id, date_str=today_str, db=db)
    if stats_resp.get("status") != "ok":
        return {"status": "error", "suggestions": []}

    stats = stats_resp["stats"]
    goals = stats_resp["goals"]

    suggestions, provider_used, switched = await generate_suggestions_safe(
        goal_type=goals["goal_type"],
        daily_target_calories=goals["daily_calories"],
        actual_calories=stats["calories"],
        actual_protein=stats["protein_g"],
        actual_fat=stats["fat_g"],
        actual_carbs=stats["carbs_g"],
        db_session=db,
        user_id=user_id,
        target_protein=goals["daily_protein"],
        target_fat=goals["daily_fat"],
        target_carbs=goals["daily_carbs"],
    )

    return {
        "status": "ok",
        "suggestions": suggestions,
        "model": {
            "provider": provider_used,
            "switched": switched,
            "message": "服务器繁忙，已自动切换备用模型" if switched else "",
        },
    }


@router.get("/stats/weekly")
async def weekly_trend(
    user_id: str = Query("anonymous"),
    db: AsyncSession = Depends(get_db),
):
    """Get daily calorie trend for the past 7 days."""
    today = date.today()
    days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        stat = await _query_daily_stats(user_id=user_id, date_str=d.isoformat(), db=db)
        if stat.get("status") == "ok":
            days.append({
                "date": d.isoformat(),
                "weekday": ["日", "一", "二", "三", "四", "五", "六"][d.weekday()],
                "calories": stat["stats"]["calories"],
                "protein_g": stat["stats"]["protein_g"],
                "fat_g": stat["stats"]["fat_g"],
                "carbs_g": stat["stats"]["carbs_g"],
                "meal_count": stat["stats"]["meal_count"],
                "goal_calories": stat["goals"]["daily_calories"],
            })
    return {"status": "ok", "days": days}


@router.get("/stats/monthly")
async def monthly_trend(
    user_id: str = Query("anonymous"),
    db: AsyncSession = Depends(get_db),
):
    """Get daily calorie trend for the past 30 days."""
    today = date.today()
    days = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        stat = await _query_daily_stats(user_id=user_id, date_str=d.isoformat(), db=db)
        if stat.get("status") == "ok":
            days.append({
                "date": d.isoformat(),
                "weekday": ["日", "一", "二", "三", "四", "五", "六"][d.weekday()],
                "calories": stat["stats"]["calories"],
                "protein_g": stat["stats"]["protein_g"],
                "fat_g": stat["stats"]["fat_g"],
                "carbs_g": stat["stats"]["carbs_g"],
                "meal_count": stat["stats"]["meal_count"],
                "goal_calories": stat["goals"]["daily_calories"],
            })
    return {"status": "ok", "days": days}
