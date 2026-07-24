"""
Meals API — image upload & AI recognition, text input & AI parsing, list/delete.
"""
import os
import uuid
import json
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.meal import Meal
from app.models.user import User, reset_daily_free_uses
from app.services.ai_vision import recognize_food_from_image, recognize_food_safe
from app.services.ai_nutrition import get_nutrition_for_food, estimate_nutrition, get_nutrition_safe

router = APIRouter(prefix="/api/v1", tags=["meals"])

UPLOAD_DIR = "storage/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@router.post("/meals/analyze-image")
async def analyze_image(
    file: UploadFile = File(...),
    user_id: str = Form("anonymous"),
    meal_type: str = Form(""),
    lang: str = Form("zh"),
    db: AsyncSession = Depends(get_db),
):
    """Upload food photo → AI recognize → save meal records → return results."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files are supported")

    # Read content with size check
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")

    # Save image
    ext = os.path.splitext(file.filename or "photo.jpg")[1] or ".jpg"
    image_name = f"{_new_id()}{ext}"
    image_path = os.path.join(UPLOAD_DIR, image_name)
    with open(image_path, "wb") as f:
        f.write(content)

    # Check usage limit with daily reset + free uses + ad reward credits
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        # Daily reset check
        reset_daily_free_uses(user)

        is_premium = (
            user.subscription_status == "active"
            and user.subscription_expiry
            and user.subscription_expiry > datetime.utcnow()
        ) or user.license_type == "permanent"

        if not is_premium:
            if (user.remaining_daily_recognitions or 0) <= 0:
                raise HTTPException(
                    429,
                    "FREE_LIMIT_REACHED: 今日免费识别次数已用完。看广告可获额外次数，或升级到 Pro。"
                )
            # Deduct: first from daily_free_uses, then from ad_reward_credits
            if (user.daily_free_uses or 0) > 0:
                user.daily_free_uses -= 1
            elif (user.ad_reward_credits or 0) > 0:
                user.ad_reward_credits -= 1
            user.remaining_daily_recognitions -= 1

    # AI food recognition with automatic model failover
    foods, provider_used, switched = await recognize_food_safe(
        content, db_session=db, lang=lang, user_id=user_id,
    )

    # Calculate nutrition for each recognized food
    records = []
    for item in foods:
        food_name = item.get("food") or item.get("name", "未知食物")
        food_name_en = item.get("food_en", "")
        nutrition_lookup = item.get("_food_zh", food_name)
        grams = float(item.get("estimated_grams") or item.get("amount_grams", 100))
        confidence = item.get("confidence")
        source_model = item.get("source_model", "unknown")
        item_lang = item.get("lang", lang)

        per_100g, nut_provider, _ = await get_nutrition_safe(
            nutrition_lookup, db_session=db, user_id=user_id,
        )
        nutrition = estimate_nutrition(grams, per_100g)

        meal = Meal(
            id=_new_id(),
            user_id=user_id,
            meal_type=meal_type,
            food_name=food_name,
            description=item.get("description", ""),
            image_path=image_path,
            source="image",
            calories=nutrition["calories"],
            protein_g=nutrition["protein_g"],
            fat_g=nutrition["fat_g"],
            carbs_g=nutrition["carbs_g"],
            created_at=datetime.utcnow(),
        )
        db.add(meal)
        records.append({
            "id": meal.id,
            "food": food_name,
            "food_en": food_name_en,
            "grams": grams,
            **nutrition,
        })
        if confidence is not None:
            records[-1]["confidence"] = confidence
        if source_model:
            records[-1]["source_model"] = source_model
        records[-1]["lang"] = item_lang

    await db.commit()

    # Return provider info for frontend status display
    model_status = {
        "provider": provider_used,
        "switched": switched,
        "message": "服务器繁忙，已自动切换备用模型" if switched else "",
    }
    return {
        "status": "ok",
        "count": len(records),
        "records": records,
        "image_path": image_path,
        "model": model_status,
    }


@router.post("/meals/analyze-text")
async def analyze_text(
    text: str = Form(...),
    user_id: str = Form("anonymous"),
    meal_type: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Parse food text → AI estimate → save meal records."""
    # Simple rule-based food splitting by common delimiters
    import re
    food_items = re.split(r"[，,、+和与及/、\s]+", text)
    food_items = [f.strip() for f in food_items if f.strip()]

    if not food_items:
        raise HTTPException(400, "No food items found in text")

    records = []
    for food_text in food_items:
        # rough gram estimation from text
        grams = 150  # default
        gram_match = re.search(r"(\d+)\s*克|(\d+)\s*g", food_text)
        if gram_match:
            grams = float(gram_match.group(1) or gram_match.group(2))
            # Remove the gram info for clean food name
            food_clean = re.sub(r"(\d+)\s*克|(\d+)\s*g", "", food_text).strip()
        else:
            food_clean = food_text
            # Estimate serving from keywords
            if "碗" in food_clean:
                grams = 200
            elif "块" in food_clean or "片" in food_clean:
                grams = 150
            elif "盘" in food_clean:
                grams = 200
            elif "个" in food_clean:
                grams = 100

        per_100g = await get_nutrition_for_food(food_clean)
        nutrition = estimate_nutrition(grams, per_100g)

        meal = Meal(
            id=_new_id(),
            user_id=user_id,
            meal_type=meal_type,
            food_name=food_clean,
            description=text,
            source="text",
            calories=nutrition["calories"],
            protein_g=nutrition["protein_g"],
            fat_g=nutrition["fat_g"],
            carbs_g=nutrition["carbs_g"],
            created_at=datetime.utcnow(),
        )
        db.add(meal)
        records.append({
            "id": meal.id,
            "food": food_clean,
            "grams": grams,
            **nutrition,
        })

    await db.commit()
    return {"status": "ok", "count": len(records), "records": records, "raw_text": text}


@router.get("/meals")
async def list_meals(
    user_id: str = "anonymous",
    date: str = "",
    db: AsyncSession = Depends(get_db),
):
    """List meal records for a user, optionally filtered by date (YYYY-MM-DD)."""
    query = select(Meal).where(Meal.user_id == user_id)

    if date:
        try:
            day_start = datetime.strptime(date, "%Y-%m-%d")
            day_end = day_start.replace(hour=23, minute=59, second=59)
            query = query.where(Meal.created_at >= day_start).where(Meal.created_at <= day_end)
        except ValueError:
            pass

    query = query.order_by(Meal.created_at.desc())
    result = await db.execute(query)
    meals = result.scalars().all()

    return {
        "status": "ok",
        "count": len(meals),
        "meals": [
            {
                "id": m.id,
                "food_name": m.food_name,
                "description": m.description,
                "source": m.source,
                "image_path": m.image_path,
                "meal_type": m.meal_type,
                "calories": m.calories,
                "protein_g": m.protein_g,
                "fat_g": m.fat_g,
                "carbs_g": m.carbs_g,
                "created_at": m.created_at.isoformat(),
            }
            for m in meals
        ],
    }


@router.delete("/meals/{meal_id}")
async def delete_meal(meal_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a meal record and its associated image file."""
    result = await db.execute(select(Meal).where(Meal.id == meal_id))
    meal = result.scalar_one_or_none()
    if not meal:
        raise HTTPException(404, "Meal not found")

    # Delete associated image file
    if meal.image_path and os.path.exists(meal.image_path):
        try:
            os.remove(meal.image_path)
        except OSError:
            pass  # Non-critical — log silently

    await db.delete(meal)
    await db.commit()
    return {"status": "ok", "deleted": meal_id}
