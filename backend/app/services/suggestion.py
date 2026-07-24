"""
AI Suggestion Service — generates simple dietary advice based on today's intake vs goals.
"""
import os
import json
import logging
import time
import httpx

logger = logging.getLogger(__name__)

AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://api.lk888.ai")
AI_API_KEY = os.getenv("AI_API_KEY", "")

SUGGEST_PROMPT = (
    "你是一个饮食助手。根据用户的目标和今日摄入，给出2-3条简洁、具体的饮食建议。"
    "返回JSON数组，每条建议包含：{\"icon\": \"emoji\", \"title\": \"短标题\", \"detail\": \"一句话建议\"}"
)


async def generate_suggestions(
    goal_type: str,
    daily_target_calories: float,
    actual_calories: float,
    actual_protein: float,
    actual_fat: float,
    actual_carbs: float,
    target_protein: float = 60,
    target_fat: float = 65,
    target_carbs: float = 300,
) -> list[dict]:
    """
    Generate 2-3 dietary suggestions based on today's intake vs goals.
    Falls back to rule-based suggestions on API failure.
    """
    # Build comparison data
    cal_diff = actual_calories - daily_target_calories
    protein_pct = (actual_protein / target_protein * 100) if target_protein > 0 else 100
    fat_pct = (actual_fat / target_fat * 100) if target_fat > 0 else 100
    carbs_pct = (actual_carbs / target_carbs * 100) if target_carbs > 0 else 100

    # Try AI API first
    api_key = AI_API_KEY
    if api_key:
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SUGGEST_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"用户目标: {goal_type}\n"
                        f"目标卡路里: {daily_target_calories:.0f}, 已摄入: {actual_calories:.0f} ({cal_diff:+.0f})\n"
                        f"蛋白质: {actual_protein:.0f}g / {target_protein:.0f}g ({protein_pct:.0f}%)\n"
                        f"脂肪: {actual_fat:.0f}g / {target_fat:.0f}g ({fat_pct:.0f}%)\n"
                        f"碳水: {actual_carbs:.0f}g / {target_carbs:.0f}g ({carbs_pct:.0f}%)"
                    ),
                },
            ],
            "temperature": 0.3,
            "max_tokens": 512,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{AI_API_BASE_URL}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
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
            logger.error(f"Suggestion API error: {e}")

    # Rule-based fallback
    suggestions = []
    if cal_diff > 300:
        suggestions.append({
            "icon": "⚠️", "title": "热量超标",
            "detail": f"今日超标 {cal_diff:.0f} 千卡，建议晚餐减少主食份量。"
        })
    elif cal_diff < -300:
        suggestions.append({
            "icon": "💪", "title": "热量不足",
            "detail": f"今日缺口 {abs(cal_diff):.0f} 千卡，建议补充优质蛋白和碳水。"
        })
    if protein_pct < 80:
        suggestions.append({
            "icon": "🥩", "title": "蛋白质偏低",
            "detail": f"蛋白质仅完成 {protein_pct:.0f}%，建议加鸡胸肉、鸡蛋或豆制品。"
        })
    if carbs_pct > 120:
        suggestions.append({
            "icon": "🍚", "title": "碳水偏高",
            "detail": f"碳水摄入超出 {carbs_pct - 100:.0f}%，建议减少精制碳水，增加蔬菜。"
        })
    if fat_pct > 120:
        suggestions.append({
            "icon": "🥑", "title": "脂肪偏高",
            "detail": "脂肪摄入偏高，注意减少油炸和加工食品。"
        })
    if not suggestions:
        suggestions.append({
            "icon": "🎉", "title": "今日达标",
            "detail": "各项营养指标均在合理范围内，继续保持！"
        })
    return suggestions


# ── Safe wrapper with model_router integration ──

async def generate_suggestions_safe(
    goal_type: str,
    daily_target_calories: float,
    actual_calories: float,
    actual_protein: float,
    actual_fat: float,
    actual_carbs: float,
    db_session,
    user_id: str = "",
    target_protein: float = 60,
    target_fat: float = 65,
    target_carbs: float = 300,
) -> tuple[list[dict], str, bool]:
    """
    Generate suggestions with automatic model failover.
    
    Returns:
        (suggestions, provider_used, switched)
    """
    from app.services.model_router import call_with_fallback

    cal_diff = actual_calories - daily_target_calories
    protein_pct = (actual_protein / target_protein * 100) if target_protein > 0 else 100
    fat_pct = (actual_fat / target_fat * 100) if target_fat > 0 else 100
    carbs_pct = (actual_carbs / target_carbs * 100) if target_carbs > 0 else 100

    async def _suggestion_api_call():
        """Call DeepSeek for AI suggestions."""
        api_key = AI_API_KEY
        if not api_key:
            return None, 0, "error", "no_api_key", 0

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SUGGEST_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"用户目标: {goal_type}\n"
                        f"目标卡路里: {daily_target_calories:.0f}, 已摄入: {actual_calories:.0f} ({cal_diff:+.0f})\n"
                        f"蛋白质: {actual_protein:.0f}g / {target_protein:.0f}g ({protein_pct:.0f}%)\n"
                        f"脂肪: {actual_fat:.0f}g / {target_fat:.0f}g ({fat_pct:.0f}%)\n"
                        f"碳水: {actual_carbs:.0f}g / {target_carbs:.0f}g ({carbs_pct:.0f}%)"
                    ),
                },
            ],
            "temperature": 0.3,
            "max_tokens": 512,
        }
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{AI_API_BASE_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        elapsed_ms = (time.monotonic() - start) * 1000

        if resp.status_code == 200:
            content = (resp.json().get("choices") or [{}])[0].get("message", {}).get("content", "")
            content = content.strip().removeprefix("```").removeprefix("json").strip()
            if "```" in content:
                content = content.split("```")[0]
            data = json.loads(content)
            if isinstance(data, list) and len(data) > 0:
                return data, elapsed_ms, "success", "", 0
        return None, elapsed_ms, "error", f"http_{resp.status_code}", 0

    result, provider, switched, error_info = await call_with_fallback(
        db_session=db_session,
        provider_calls=[
            {"provider": "deepseek", "call": _suggestion_api_call},
        ],
        user_id=user_id,
        endpoint="/api/v1/stats/suggestions",
    )

    if result is not None:
        return result, provider, switched

    # Fallback to rule-based (same module)
    logger.warning("Suggestion API failed, using rule-based: %s", error_info)
    rule_result = await generate_suggestions(
        goal_type, daily_target_calories, actual_calories,
        actual_protein, actual_fat, actual_carbs,
        target_protein, target_fat, target_carbs,
    )
    return rule_result, "fallback", switched
