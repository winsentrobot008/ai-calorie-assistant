"""
AI Trend Analysis — computes daily calorie changes, weekly/monthly trends,
and meal-type distribution for chart visualization.
"""
import logging
from datetime import date, timedelta, datetime as dt
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meal import Meal
from app.models.user import User
from app.models.trend import TrendCache

logger = logging.getLogger(__name__)


async def get_daily_trend(
    user_id: str,
    days: int = 7,
    db: AsyncSession = None,
) -> list[dict]:
    """
    Get daily calorie trend with meal-type distribution for the past N days.
    Returns list of {date, weekday, calories, protein_g, fat_g, carbs_g,
                      meal_count, goal_calories, meal_types: {...}}
    """
    today = date.today()
    result = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        day_data = await _compute_daily_stats(user_id, d.isoformat(), db)
        result.append(day_data)
    return result


async def _compute_daily_stats(
    user_id: str, date_str: str, db: AsyncSession
) -> dict:
    """Compute daily stats including meal-type breakdown."""
    try:
        day_start = dt.strptime(date_str, "%Y-%m-%d")
        day_end = day_start.replace(hour=23, minute=59, second=59)
    except ValueError:
        return {"date": date_str, "calories": 0}

    # Aggregated query
    query = select(
        func.coalesce(func.sum(Meal.calories), 0).label("total_cal"),
        func.coalesce(func.sum(Meal.protein_g), 0).label("total_protein"),
        func.coalesce(func.sum(Meal.fat_g), 0).label("total_fat"),
        func.coalesce(func.sum(Meal.carbs_g), 0).label("total_carbs"),
        func.count(Meal.id).label("meal_count"),
    ).where(
        Meal.user_id == user_id,
        Meal.created_at >= day_start,
        Meal.created_at <= day_end,
    )
    row = (await db.execute(query)).one()

    # Meal-type breakdown
    meal_types = {"breakfast": 0, "lunch": 0, "dinner": 0, "snack": 0}
    for mt in meal_types:
        mt_query = select(
            func.coalesce(func.sum(Meal.calories), 0)
        ).where(
            Meal.user_id == user_id,
            Meal.meal_type == mt,
            Meal.created_at >= day_start,
            Meal.created_at <= day_end,
        )
        mt_cal = (await db.execute(mt_query)).scalar()
        meal_types[mt] = round(mt_cal, 1)

    # User goals
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    goal_cal = user.daily_calories if user else 2000

    return {
        "date": date_str,
        "weekday": ["日", "一", "二", "三", "四", "五", "六"][day_start.weekday()],
        "calories": round(row.total_cal, 1),
        "protein_g": round(row.total_protein, 1),
        "fat_g": round(row.total_fat, 1),
        "carbs_g": round(row.total_carbs, 1),
        "meal_count": row.meal_count,
        "goal_calories": goal_cal,
        "meal_types": meal_types,
    }


async def update_trend_cache(user_id: str, db: AsyncSession):
    """Update TrendCache for today after a meal is added."""
    today_str = date.today().isoformat()
    stats = await _compute_daily_stats(user_id, today_str, db)

    # Upsert cache
    existing = await db.execute(
        select(TrendCache).where(
            TrendCache.user_id == user_id,
            TrendCache.date == today_str,
        )
    )
    cache = existing.scalar_one_or_none()

    if cache:
        cache.total_calories = stats["calories"]
        cache.total_protein = stats["protein_g"]
        cache.total_fat = stats["fat_g"]
        cache.total_carbs = stats["carbs_g"]
        cache.meal_count = stats["meal_count"]
        cache.meal_type_calories = stats["meal_types"]
        cache.updated_at = dt.utcnow()
    else:
        import uuid
        cache = TrendCache(
            id=uuid.uuid4().hex[:12],
            user_id=user_id,
            date=today_str,
            total_calories=stats["calories"],
            total_protein=stats["protein_g"],
            total_fat=stats["fat_g"],
            total_carbs=stats["carbs_g"],
            meal_count=stats["meal_count"],
            meal_type_calories=stats["meal_types"],
            updated_at=dt.utcnow(),
        )
        db.add(cache)

    await db.commit()
    logger.info(f"TrendCache updated for {user_id} / {today_str}")
