"""
User model — stores profile, daily goals, auth info, billing & subscription.
"""
from datetime import datetime, date
from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer
from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)       # anonymous id or email
    name = Column(String, default="")
    email = Column(String, default="", index=True)
    password_hash = Column(String, default="")

    # ── Daily Goals ──
    goal_type = Column(String, default="maintain")  # lose / gain / maintain
    daily_calories = Column(Float, default=2000.0)
    daily_protein = Column(Float, default=60.0)
    daily_fat = Column(Float, default=65.0)
    daily_carbs = Column(Float, default=300.0)

    # ── Subscription ──
    subscription_status = Column(String, default="free")  # free / active / expired / cancelled
    subscription_plan = Column(String, default="")        # monthly / yearly / ""
    subscription_expiry = Column(DateTime, nullable=True)
    stripe_customer_id = Column(String, default="", index=True)
    stripe_subscription_id = Column(String, default="")

    # ── License (One-time purchase) ──
    license_type = Column(String, default="free")  # free / permanent
    license_purchased_at = Column(DateTime, nullable=True)

    # ── Free-tier limits ──
    daily_free_uses = Column(Integer, default=1)           # 每日免费次数 (default 1)
    daily_free_date = Column(String, default="")            # 上次重置日期的 YYYY-MM-DD
    remaining_daily_recognitions = Column(Integer, default=1)  # 当前剩余次数(包含免费+广告积分)
    ad_reward_credits = Column(Integer, default=0)          # 广告积分

    # ── Daily nutrition limit ──
    max_daily_calories = Column(Float, default=5000.0)     # 每日最大卡路里限制

    # ── Admin ──
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # ── Timestamps ──
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def reset_daily_free_uses(user: User) -> bool:
    """
    Check if the user needs a daily reset of free uses.
    Returns True if reset was performed.
    """
    today = date.today().isoformat()
    if user.daily_free_date != today:
        user.daily_free_uses = 1
        user.daily_free_date = today
        # Recalculate remaining = free_uses + ad_credits
        user.remaining_daily_recognitions = user.daily_free_uses + (user.ad_reward_credits or 0)
        return True
    return False
