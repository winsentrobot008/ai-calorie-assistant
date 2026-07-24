"""
Meal model — a single food entry with AI-estimated nutrition.
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text
from app.db import Base


class Meal(Base):
    __tablename__ = "meals"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, default="anonymous")
    meal_type = Column(String, default="")  # breakfast / lunch / dinner / snack
    food_name = Column(String, default="")
    description = Column(Text, default="")        # raw user text or AI description
    image_path = Column(String, default="")       # saved image path
    source = Column(String, default="text")       # "text" | "image"

    calories = Column(Float, default=0.0)
    protein_g = Column(Float, default=0.0)
    fat_g = Column(Float, default=0.0)
    carbs_g = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
