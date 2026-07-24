"""
AI Nutrition Service — estimates calories, protein, fat, carbs from food text.
Uses the universal AI API (OpenAI-compatible chat completion).
Falls back to a built-in food database on API failure.
"""
import os
import json
import logging
import time
import httpx

logger = logging.getLogger(__name__)

AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://api.lk888.ai")
AI_API_KEY = os.getenv("AI_API_KEY", "")

NUTRITION_PROMPT = (
    "You are a nutrition database. For each food item below, return nutrition per 100g. "
    "Return ONLY valid JSON array with NO markdown, NO code fences:\n"
    '[{"food": "exact food name in Chinese", "calories_per_100g": number, '
    '"protein_per_100g": number, "fat_per_100g": number, "carbs_per_100g": number}]\n'
    "Use standard Chinese food nutrition data. Be precise."
)

# Built-in fallback food DB (per 100g)
# 100+ world food entries organized by category
FOOD_DB = {
    # ── 米饭/主食 ──
    "白米饭":     {"calories": 116, "protein": 2.6, "fat": 0.3, "carbs": 25.9},
    "米饭":       {"calories": 116, "protein": 2.6, "fat": 0.3, "carbs": 25.9},
    "炒饭":       {"calories": 220, "protein": 5.0, "fat": 8.0, "carbs": 32.0},
    "米粥":       {"calories": 46,  "protein": 1.0, "fat": 0.2, "carbs": 9.5},
    "寿司":       {"calories": 150, "protein": 5.0, "fat": 2.0, "carbs": 28.0},
    "咖喱饭":     {"calories": 200, "protein": 6.0, "fat": 5.0, "carbs": 33.0},
    "印度香饭":   {"calories": 240, "protein": 6.0, "fat": 8.0, "carbs": 36.0},
    "意大利烩饭": {"calories": 180, "protein": 5.0, "fat": 6.0, "carbs": 28.0},
    # ── 面条/面食 ──
    "面条":       {"calories": 110, "protein": 3.5, "fat": 0.5, "carbs": 24.0},
    "拉面":       {"calories": 140, "protein": 4.0, "fat": 2.0, "carbs": 27.0},
    "意大利肉酱面":{"calories": 160, "protein": 6.0, "fat": 4.0, "carbs": 26.0},
    "奶油培根面": {"calories": 200, "protein": 8.0, "fat": 10.0, "carbs": 20.0},
    "千层面":     {"calories": 180, "protein": 8.0, "fat": 7.0, "carbs": 22.0},
    "越南河粉":   {"calories": 90,  "protein": 4.0, "fat": 1.0, "carbs": 17.0},
    # ── 包子/饺子/点心 ──
    "包子":       {"calories": 233, "protein": 8.0, "fat": 3.0, "carbs": 44.0},
    "饺子":       {"calories": 220, "protein": 9.0, "fat": 6.0, "carbs": 34.0},
    "煎饺":       {"calories": 250, "protein": 8.0, "fat": 10.0, "carbs": 32.0},
    "馄饨":       {"calories": 120, "protein": 6.0, "fat": 3.0, "carbs": 18.0},
    "馄饨汤":     {"calories": 80,  "protein": 4.0, "fat": 2.0, "carbs": 12.0},
    "春卷":       {"calories": 200, "protein": 5.0, "fat": 10.0, "carbs": 24.0},
    "点心":       {"calories": 180, "protein": 6.0, "fat": 8.0, "carbs": 22.0},
    "咖喱角":     {"calories": 220, "protein": 5.0, "fat": 12.0, "carbs": 25.0},
    # ── 面包/饼类 ──
    "面包":       {"calories": 265, "protein": 9.0, "fat": 3.0, "carbs": 49.0},
    "全麦面包":   {"calories": 246, "protein": 10.0, "fat": 3.4, "carbs": 44.0},
    "法式吐司":   {"calories": 250, "protein": 7.0, "fat": 10.0, "carbs": 34.0},
    "松饼":       {"calories": 220, "protein": 5.0, "fat": 8.0, "carbs": 33.0},
    "华夫饼":     {"calories": 290, "protein": 6.0, "fat": 14.0, "carbs": 36.0},
    "馕饼":       {"calories": 260, "protein": 8.0, "fat": 5.0, "carbs": 47.0},
    "印度饼":     {"calories": 250, "protein": 7.0, "fat": 4.0, "carbs": 48.0},
    "皮塔饼":     {"calories": 220, "protein": 7.0, "fat": 2.0, "carbs": 45.0},
    "玉米饼":     {"calories": 210, "protein": 6.0, "fat": 5.0, "carbs": 38.0},
    # ── 汉堡/西式快餐 ──
    "汉堡":       {"calories": 250, "protein": 12.0, "fat": 14.0, "carbs": 22.0},
    "芝士汉堡":   {"calories": 280, "protein": 14.0, "fat": 16.0, "carbs": 22.0},
    "热狗":       {"calories": 250, "protein": 10.0, "fat": 15.0, "carbs": 22.0},
    "薯条":       {"calories": 310, "protein": 3.0, "fat": 15.0, "carbs": 41.0},
    "披萨":       {"calories": 260, "protein": 11.0, "fat": 10.0, "carbs": 33.0},
    "俱乐部三明治":{"calories": 230, "protein": 12.0, "fat": 10.0, "carbs": 24.0},
    "玉米热狗":   {"calories": 250, "protein": 8.0, "fat": 14.0, "carbs": 26.0},
    # ── 烤肉/牛排 ──
    "牛排":       {"calories": 250, "protein": 26.0, "fat": 15.0, "carbs": 0},
    "牛肉":       {"calories": 125, "protein": 20.0, "fat": 4.5, "carbs": 0},
    "烤排骨":     {"calories": 280, "protein": 22.0, "fat": 20.0, "carbs": 3.0},
    "猪排":       {"calories": 230, "protein": 25.0, "fat": 14.0, "carbs": 0},
    "烤肉":       {"calories": 220, "protein": 20.0, "fat": 15.0, "carbs": 2.0},
    "炸猪排":     {"calories": 280, "protein": 18.0, "fat": 18.0, "carbs": 12.0},
    "鸡肉卷":     {"calories": 200, "protein": 14.0, "fat": 10.0, "carbs": 16.0},
    # ── 鸡肉/禽类 ──
    "鸡胸肉":     {"calories": 133, "protein": 31.0, "fat": 1.2, "carbs": 0},
    "煎鸡胸肉":   {"calories": 155, "protein": 30.0, "fat": 3.0, "carbs": 0.5},
    "炸鸡":       {"calories": 290, "protein": 20.0, "fat": 18.0, "carbs": 10.0},
    "鸡翅":       {"calories": 220, "protein": 18.0, "fat": 16.0, "carbs": 2.0},
    "宫保鸡丁":   {"calories": 180, "protein": 14.0, "fat": 10.0, "carbs": 10.0},
    "咖喱鸡":     {"calories": 190, "protein": 16.0, "fat": 10.0, "carbs": 10.0},
    "坦都里烤鸡": {"calories": 200, "protein": 22.0, "fat": 10.0, "carbs": 4.0},
    "黄油鸡":     {"calories": 220, "protein": 18.0, "fat": 14.0, "carbs": 8.0},
    "照烧":       {"calories": 200, "protein": 18.0, "fat": 8.0, "carbs": 12.0},
    # ── 鱼类/海鲜 ──
    "三文鱼":     {"calories": 208, "protein": 20.0, "fat": 13.0, "carbs": 0},
    "烤三文鱼":   {"calories": 200, "protein": 22.0, "fat": 12.0, "carbs": 0},
    "炸鱼薯条":   {"calories": 220, "protein": 12.0, "fat": 12.0, "carbs": 18.0},
    "酸橘汁腌鱼": {"calories": 100, "protein": 15.0, "fat": 3.0, "carbs": 3.0},
    "鳗鱼":       {"calories": 230, "protein": 18.0, "fat": 16.0, "carbs": 2.0},
    # ── 蔬菜/沙拉 ──
    "西兰花":     {"calories": 34,  "protein": 2.8, "fat": 0.4, "carbs": 6.6},
    "沙拉":       {"calories": 35,  "protein": 1.5, "fat": 2.0, "carbs": 3.0},
    "凯撒沙拉":   {"calories": 100, "protein": 5.0, "fat": 7.0, "carbs": 6.0},
    "希腊沙拉":   {"calories": 80,  "protein": 3.0, "fat": 5.0, "carbs": 5.0},
    "水果沙拉":   {"calories": 90,  "protein": 1.0, "fat": 0.5, "carbs": 20.0},
    "卷心菜沙拉": {"calories": 60,  "protein": 1.0, "fat": 3.0, "carbs": 8.0},
    "甜菜沙拉":   {"calories": 70,  "protein": 1.5, "fat": 3.0, "carbs": 10.0},
    "炒青菜":     {"calories": 45,  "protein": 2.0, "fat": 2.5, "carbs": 4.0},
    "毛豆":       {"calories": 120, "protein": 11.0, "fat": 5.0, "carbs": 9.0},
    # ── 汤类 ──
    "味噌汤":     {"calories": 30,  "protein": 2.0, "fat": 1.0, "carbs": 3.0},
    "番茄汤":     {"calories": 50,  "protein": 1.5, "fat": 1.0, "carbs": 9.0},
    "蛤蜊浓汤":   {"calories": 90,  "protein": 4.0, "fat": 5.0, "carbs": 8.0},
    "龙虾浓汤":   {"calories": 120, "protein": 6.0, "fat": 7.0, "carbs": 8.0},
    "酸辣汤":     {"calories": 60,  "protein": 3.0, "fat": 2.0, "carbs": 7.0},
    "蛋花汤":     {"calories": 35,  "protein": 3.0, "fat": 1.5, "carbs": 2.0},
    "扁豆汤":     {"calories": 90,  "protein": 6.0, "fat": 1.0, "carbs": 15.0},
    # ── 鸡蛋/早餐 ──
    "鸡蛋":       {"calories": 143, "protein": 12.6, "fat": 9.5, "carbs": 1.5},
    "煎蛋":       {"calories": 196, "protein": 13.0, "fat": 15.0, "carbs": 1.0},
    "煎蛋卷":     {"calories": 180, "protein": 12.0, "fat": 13.0, "carbs": 2.0},
    "炒蛋":       {"calories": 200, "protein": 14.0, "fat": 15.0, "carbs": 2.0},
    "班尼迪克蛋": {"calories": 250, "protein": 15.0, "fat": 18.0, "carbs": 10.0},
    "油条":       {"calories": 386, "protein": 7.0, "fat": 17.0, "carbs": 52.0},
    # ── 豆制品 ──
    "豆腐":       {"calories": 76,  "protein": 8.0, "fat": 4.8, "carbs": 1.9},
    "麻婆豆腐":   {"calories": 120, "protein": 8.0, "fat": 7.0, "carbs": 6.0},
    "豆浆":       {"calories": 40,  "protein": 3.0, "fat": 1.5, "carbs": 2.0},
    "鹰嘴豆泥":   {"calories": 160, "protein": 5.0, "fat": 10.0, "carbs": 15.0},
    # ── 意面/意大利 ──
    "意面":       {"calories": 160, "protein": 6.0, "fat": 4.0, "carbs": 26.0},
    # ── 甜点/烘焙 ──
    "甜甜圈":     {"calories": 350, "protein": 5.0, "fat": 18.0, "carbs": 44.0},
    "冰淇淋":     {"calories": 200, "protein": 3.5, "fat": 11.0, "carbs": 24.0},
    "纸杯蛋糕":   {"calories": 300, "protein": 3.0, "fat": 15.0, "carbs": 40.0},
    "苹果派":     {"calories": 240, "protein": 2.0, "fat": 11.0, "carbs": 34.0},
    "焦糖布丁":   {"calories": 250, "protein": 4.0, "fat": 18.0, "carbs": 20.0},
    "芝士蛋糕":   {"calories": 320, "protein": 6.0, "fat": 22.0, "carbs": 26.0},
    "巧克力蛋糕": {"calories": 350, "protein": 4.0, "fat": 20.0, "carbs": 40.0},
    "提拉米苏":   {"calories": 330, "protein": 5.0, "fat": 22.0, "carbs": 28.0},
    "布朗尼":     {"calories": 400, "protein": 5.0, "fat": 25.0, "carbs": 42.0},
    "马卡龙":     {"calories": 280, "protein": 3.0, "fat": 14.0, "carbs": 36.0},
    "果仁蜜饼":   {"calories": 330, "protein": 5.0, "fat": 20.0, "carbs": 34.0},
    "面包布丁":   {"calories": 220, "protein": 5.0, "fat": 10.0, "carbs": 28.0},
    "西班牙油条": {"calories": 280, "protein": 3.0, "fat": 14.0, "carbs": 36.0},
    # ── 拉丁美食 ──
    "墨西哥卷饼": {"calories": 180, "protein": 8.0, "fat": 8.0, "carbs": 20.0},
    "墨西哥卷":   {"calories": 240, "protein": 10.0, "fat": 10.0, "carbs": 28.0},
    "玉米片":     {"calories": 280, "protein": 6.0, "fat": 15.0, "carbs": 32.0},
    "牛油果酱":   {"calories": 160, "protein": 2.0, "fat": 15.0, "carbs": 8.0},
    "玉米粽":     {"calories": 200, "protein": 5.0, "fat": 8.0, "carbs": 28.0},
    # ── 地中海 ──
    "法拉费":     {"calories": 200, "protein": 8.0, "fat": 10.0, "carbs": 22.0},
    "希腊烤肉":   {"calories": 210, "protein": 16.0, "fat": 12.0, "carbs": 10.0},
    # ── 日式 ──
    "章鱼烧":     {"calories": 180, "protein": 5.0, "fat": 8.0, "carbs": 22.0},
    "大阪烧":     {"calories": 180, "protein": 6.0, "fat": 8.0, "carbs": 22.0},
    "天妇罗":     {"calories": 200, "protein": 6.0, "fat": 12.0, "carbs": 18.0},
    # ── 中国菜 ──
    "火锅":       {"calories": 100, "protein": 8.0, "fat": 5.0, "carbs": 5.0},
    "糖醋里脊":   {"calories": 200, "protein": 14.0, "fat": 8.0, "carbs": 20.0},
    # ── 饮品 ──
    "牛奶":       {"calories": 42,  "protein": 3.4, "fat": 1.0, "carbs": 5.0},
    "酸奶":       {"calories": 61,  "protein": 3.5, "fat": 1.5, "carbs": 6.8},
    # ── 水果 ──
    "香蕉":       {"calories": 89,  "protein": 1.1, "fat": 0.3, "carbs": 22.8},
    "苹果":       {"calories": 52,  "protein": 0.3, "fat": 0.2, "carbs": 14.0},
    # ── 根茎类 ──
    "红薯":       {"calories": 86,  "protein": 1.6, "fat": 0.1, "carbs": 20.0},
    "土豆":       {"calories": 77,  "protein": 2.0, "fat": 0.1, "carbs": 17.5},
}

# Default nutrition for unknown foods
DEFAULT_NUTRITION = {"calories": 100, "protein": 5.0, "fat": 3.0, "carbs": 15.0}


async def get_nutrition_for_food(food_name: str) -> dict:
    """Look up or AI-estimate nutrition for a single food item (per 100g)."""
    # 1. Check built-in DB first
    name_lower = food_name.lower().strip()
    for key, val in FOOD_DB.items():
        if key in food_name or food_name in key:
            return val

    # 2. Try AI API
    api_key = AI_API_KEY
    if api_key:
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": NUTRITION_PROMPT},
                {"role": "user", "content": f"Food: {food_name}"},
            ],
            "temperature": 0.1,
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
                        item = data[0]
                        return {
                            "calories": item.get("calories_per_100g", 100),
                            "protein": item.get("protein_per_100g", 5),
                            "fat": item.get("fat_per_100g", 3),
                            "carbs": item.get("carbs_per_100g", 15),
                        }
        except Exception as e:
            logger.error(f"AI Nutrition API error for '{food_name}': {e}")

    return dict(DEFAULT_NUTRITION)


def estimate_nutrition(grams: float, per_100g: dict) -> dict:
    """Scale per-100g nutrition to actual serving size."""
    factor = grams / 100.0
    return {
        "calories": round(per_100g["calories"] * factor, 1),
        "protein_g": round(per_100g["protein"] * factor, 1),
        "fat_g": round(per_100g["fat"] * factor, 1),
        "carbs_g": round(per_100g["carbs"] * factor, 1),
    }


# ── Safe wrapper with model_router integration ──

async def get_nutrition_safe(
    food_name: str,
    db_session,
    user_id: str = "",
) -> tuple[dict, str, bool]:
    """
    Get nutrition data with automatic model failover.
    
    Priority: Built-in DB → DeepSeek API → Default nutrition.
    
    Returns:
        (nutrition_data, provider_used, switched)
    """
    # 1. Check built-in DB first (local, no health check needed)
    name_lower = food_name.lower().strip()
    for key, val in FOOD_DB.items():
        if key in food_name or food_name in key:
            return val, "local_db", False

    # 2. Try AI API with model_router
    from app.services.model_router import call_with_fallback

    async def _nutrition_api_call():
        """Call DeepSeek for nutrition estimation."""
        api_key = AI_API_KEY
        if not api_key:
            return None, 0, "error", "no_api_key", 0

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": NUTRITION_PROMPT},
                {"role": "user", "content": f"Food: {food_name}"},
            ],
            "temperature": 0.1,
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
                item = data[0]
                result = {
                    "calories": item.get("calories_per_100g", 100),
                    "protein": item.get("protein_per_100g", 5),
                    "fat": item.get("fat_per_100g", 3),
                    "carbs": item.get("carbs_per_100g", 15),
                }
                return result, elapsed_ms, "success", "", 0
        return None, elapsed_ms, "error" if resp.status_code != 200 else "parse_error", f"http_{resp.status_code}", 0

    result, provider, switched, error_info = await call_with_fallback(
        db_session=db_session,
        provider_calls=[
            {"provider": "deepseek", "call": _nutrition_api_call},
        ],
        user_id=user_id,
        endpoint="/api/v1/meals/nutrition",
    )

    if result is not None:
        return result, provider, switched

    # 3. Fallback to default
    logger.warning("Nutrition API failed, using default for '%s': %s", food_name, error_info)
    return dict(DEFAULT_NUTRITION), "fallback", switched
