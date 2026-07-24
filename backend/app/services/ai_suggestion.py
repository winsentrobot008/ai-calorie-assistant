"""
AI Suggestion Service — generates personalized dietary advice based on
recent 7-day eating patterns, nutritional gaps, and user goals (lose/gain/maintain).
Falls back to rule-based logic on API failure.
"""
import os
import json
import uuid
import logging
from datetime import date, timedelta, datetime as dt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.models.user import User
from app.models.meal import Meal
from app.models.trend import Suggestion as SuggestionModel
from app.services.ai_trend import get_daily_trend

logger = logging.getLogger(__name__)

AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://api.lk888.ai")
AI_API_KEY = os.getenv("AI_API_KEY", "")

SEVEN_DAY_PROMPT = (
    "你是一个营养分析师。根据用户过去7天的饮食数据和目标，给出2-3条有洞察力的个性化建议。"
    "注意观察趋势（是否每天都超标/不足、营养是否均衡等）。"
    "返回JSON数组，每条包含：{\"icon\": \"emoji\", \"title\": \"短标题\", \"detail\": \"一句话建议\"}"
    "建议要具体、可执行，不要泛泛而谈。"
)


async def generate_7day_suggestions(
    user_id: str,
    db: AsyncSession,
) -> list[dict]:
    """
    Generate suggestions based on 7-day eating patterns + user goals.
    Saves results to the suggestions table.
    """
    # Get user goals
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    goal_type = user.goal_type if user else "maintain"
    target_cal = user.daily_calories if user else 2000
    target_protein = user.daily_protein if user else 60
    target_fat = user.daily_fat if user else 65
    target_carbs = user.daily_carbs if user else 300

    # Get 7-day trend
    trend = await get_daily_trend(user_id, days=7, db=db)
    today_stats = trend[-1] if trend else {}

    # Compute averages and patterns
    days_with_data = [d for d in trend if d.get("calories", 0) > 0]
    avg_cal = sum(d["calories"] for d in days_with_data) / max(len(days_with_data), 1)
    avg_protein = sum(d["protein_g"] for d in days_with_data) / max(len(days_with_data), 1)
    avg_fat = sum(d["fat_g"] for d in days_with_data) / max(len(days_with_data), 1)
    avg_carbs = sum(d["carbs_g"] for d in days_with_data) / max(len(days_with_data), 1)
    over_count = sum(1 for d in days_with_data if d["calories"] > target_cal)

    # Try AI API with 7-day context
    suggestions = await _call_ai_with_context(
        goal_type, target_cal, avg_cal, avg_protein, avg_fat, avg_carbs,
        target_protein, target_fat, target_carbs, over_count, len(days_with_data),
    )

    if not suggestions:
        # Rule-based fallback with 7-day insight
        suggestions = _rule_based_7day(
            goal_type, target_cal, avg_cal, today_stats,
            avg_protein, avg_fat, avg_carbs,
            target_protein, target_fat, target_carbs,
            over_count, len(days_with_data),
        )

    # Save to database
    today_str = date.today().isoformat()
    model = SuggestionModel(
        id=uuid.uuid4().hex[:12],
        user_id=user_id,
        date=today_str,
        goal_type=goal_type,
        suggestions=suggestions,
        source="api" if suggestions else "rule",
        created_at=dt.utcnow(),
    )
    db.add(model)
    await db.commit()

    return suggestions


async def _call_ai_with_context(
    goal_type, target_cal, avg_cal, avg_protein, avg_fat, avg_carbs,
    target_protein, target_fat, target_carbs, over_count, data_days,
) -> list[dict]:
    """Call AI API with 7-day context."""
    if not AI_API_KEY:
        return []

    cal_diff = avg_cal - target_cal
    context = (
        f"用户目标: {goal_type}\n"
        f"7天平均摄入: {avg_cal:.0f} kcal (目标 {target_cal:.0f}, 日均差 {cal_diff:+.0f})\n"
        f"超标天数: {over_count}/{data_days}\n"
        f"蛋白质平均: {avg_protein:.0f}g / {target_protein:.0f}g\n"
        f"脂肪平均: {avg_fat:.0f}g / {target_fat:.0f}g\n"
        f"碳水平均: {avg_carbs:.0f}g / {target_carbs:.0f}g\n"
        f"有数据天数: {data_days}/7"
    )

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SEVEN_DAY_PROMPT},
            {"role": "user", "content": context},
        ],
        "temperature": 0.3,
        "max_tokens": 512,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{AI_API_BASE_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code == 200:
                content = (resp.json().get("choices") or [{}])[0].get("message", {}).get("content", "")
                content = content.strip().removeprefix("```").removeprefix("json").strip()
                if "```" in content:
                    content = content.split("```")[0]
                data = json.loads(content)
                if isinstance(data, list) and len(data) > 0:
                    return data
    except Exception as e:
        logger.error(f"7-day suggestion API error: {e}")
    return []


def _rule_based_7day(
    goal_type, target_cal, avg_cal, today_stats,
    avg_protein, avg_fat, avg_carbs,
    target_protein, target_fat, target_carbs,
    over_count, data_days,
) -> list[dict]:
    """Rule-based suggestions using 7-day averages + goal type."""
    suggestions = []

    # Calorie assessment
    cal_diff = avg_cal - target_cal
    if goal_type == "lose":
        if cal_diff > 100:
            suggestions.append({
                "icon": "⚠️", "title": "减脂期热量偏高",
                "detail": f"过去7天日均超目标 {cal_diff:.0f} kcal，建议控制晚餐碳水、增加蔬菜体积。"
            })
        elif cal_diff < -100:
            suggestions.append({
                "icon": "✅", "title": "热量控制良好",
                "detail": f"日均摄入 {avg_cal:.0f} kcal，低于目标 {abs(cal_diff):.0f} kcal，适合减脂节奏。"
            })
    elif goal_type == "gain":
        if cal_diff < 100:
            suggestions.append({
                "icon": "💪", "title": "增肌期热量不足",
                "detail": f"日均 {avg_cal:.0f} kcal，建议加餐坚果、牛奶或蛋白粉。"
            })
        elif cal_diff > 300:
            suggestions.append({
                "icon": "✅", "title": "热量充足",
                "detail": f"日均超目标 {cal_diff:.0f} kcal，增肌效果良好。"
            })
    else:
        if abs(cal_diff) > 300:
            suggestions.append({
                "icon": "⚖️", "title": "热量波动较大",
                "detail": f"日均 {avg_cal:.0f} kcal，偏离目标 {abs(cal_diff):.0f} kcal，建议调整饮食结构。"
            })

    # Protein (critical for all goals)
    protein_ratio = avg_protein / target_protein * 100 if target_protein > 0 else 100
    if protein_ratio < 70:
        suggestions.append({
            "icon": "🥩", "title": "蛋白质长期不足",
            "detail": f"7天平均蛋白质 {avg_protein:.0f}g，仅达目标 {protein_ratio:.0f}%，建议每餐加入鸡胸肉/鸡蛋/豆制品。"
        })
    elif protein_ratio > 130:
        suggestions.append({
            "icon": "🥩", "title": "蛋白质充足",
            "detail": f"蛋白质摄入良好（{avg_protein:.0f}g/日），注意搭配足够蔬菜。"
        })

    # Carb/Fat balance
    carb_ratio = avg_carbs / target_carbs * 100 if target_carbs > 0 else 100
    fat_ratio = avg_fat / target_fat * 100 if target_fat > 0 else 100
    if carb_ratio > 130:
        suggestions.append({
            "icon": "🍚", "title": "碳水偏高",
            "detail": f"7天平均碳水超出 {carb_ratio - 100:.0f}%，建议减少精制碳水，替换为粗粮。"
        })
    if fat_ratio > 130:
        suggestions.append({
            "icon": "🥑", "title": "脂肪偏高",
            "detail": f"7天平均脂肪超出 {fat_ratio - 100:.0f}%，注意控制油炸食品和加工零食。"
        })

    # Consistency
    if data_days < 3:
        suggestions.append({
            "icon": "📝", "title": "记录不够",
            "detail": f"过去7天仅有 {data_days} 天有记录，坚持每天记录以获得更准确的建议。"
        })
    elif over_count >= 5:
        suggestions.append({
            "icon": "📈", "title": "频繁超标",
            "detail": f"7天中有 {over_count} 天热量超标，尝试设置饮食计划或餐前喝水。"
        })

    if not suggestions:
        suggestions.append({
            "icon": "🎉", "title": "整体不错",
            "detail": f"过去7天日均 {avg_cal:.0f} kcal，营养均衡，继续保持！"
        })

    return suggestions


async def get_suggestion_history(
    user_id: str,
    days: int = 7,
    db: AsyncSession = None,
) -> list[dict]:
    """Get recent suggestion history."""
    from datetime import timedelta, date
    cutoff = date.today() - timedelta(days=days)
    result = await db.execute(
        select(SuggestionModel)
        .where(SuggestionModel.user_id == user_id, SuggestionModel.date >= cutoff.isoformat())
        .order_by(SuggestionModel.created_at.desc())
    )
    return [
        {
            "id": s.id,
            "date": s.date,
            "goal_type": s.goal_type,
            "suggestions": s.suggestions,
            "source": s.source,
            "created_at": s.created_at.isoformat(),
        }
        for s in result.scalars().all()
    ]
