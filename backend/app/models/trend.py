"""
Trend & Suggestion models — daily aggregates and AI suggestion history.
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text, JSON
from app.db import Base


class TrendCache(Base):
    """Daily aggregated nutrition statistics for fast trend queries."""
    __tablename__ = "trend_cache"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, default="anonymous")
    date = Column(String, index=True)  # YYYY-MM-DD
    total_calories = Column(Float, default=0.0)
    total_protein = Column(Float, default=0.0)
    total_fat = Column(Float, default=0.0)
    total_carbs = Column(Float, default=0.0)
    meal_count = Column(Float, default=0)
    # Meal-type breakdown (stored as JSON: {"breakfast": cal, "lunch": cal, ...})
    meal_type_calories = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Suggestion(Base):
    """AI suggestion history — stores generated dietary advice."""
    __tablename__ = "suggestions"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, default="anonymous")
    date = Column(String, index=True)  # YYYY-MM-DD
    goal_type = Column(String, default="maintain")
    suggestions = Column(JSON, default=list)  # [{icon, title, detail}, ...]
    source = Column(String, default="rule")  # "api" | "rule"
    created_at = Column(DateTime, default=datetime.utcnow)
