"""
Admin API — dashboard overview, user management, revenue, model monitoring, config.
"""
import uuid
import hashlib
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.models.billing import Invoice, AdLog
from app.models.admin import AdminUser, SystemConfig, AuditLog, ModelMonitor
from app.models.meal import Meal

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


async def _verify_admin(
    admin_id: str = "",
    admin_token: str = "",
    db: AsyncSession = None,
) -> AdminUser:
    """Simple admin auth check."""
    if not db:
        return None
    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin or not admin.is_active:
        return None
    return admin


# ── Auth ──


@router.post("/login")
async def admin_login(
    username: str = Query(...),
    password: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Admin login — returns admin_id for session."""
    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    admin = result.scalar_one_or_none()

    if not admin or admin.password_hash != _hash_password(password):
        raise HTTPException(401, "Invalid credentials")

    admin.last_login = datetime.utcnow()
    await db.commit()

    return {
        "status": "ok",
        "admin_id": admin.id,
        "username": admin.username,
        "role": admin.role,
    }


# ── System Overview ──


@router.get("/overview")
async def system_overview(
    db: AsyncSession = Depends(get_db),
):
    """System-level overview statistics."""
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    week_ago = today_start - timedelta(days=7)

    # Total users
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar() or 0

    # Today's recognitions
    today_meals = await db.execute(
        select(func.count(Meal.id)).where(Meal.created_at >= today_start)
    )
    today_recognitions = today_meals.scalar() or 0

    # Weekly meal count
    weekly_meals = await db.execute(
        select(func.count(Meal.id)).where(Meal.created_at >= week_ago)
    )
    weekly_recognitions = weekly_meals.scalar() or 0

    # Active subscriptions
    active_subs = await db.execute(
        select(func.count(User.id)).where(User.subscription_status == "active")
    )
    active_subscriptions = active_subs.scalar() or 0

    # Permanent licenses
    permanent_licenses_q = await db.execute(
        select(func.count(User.id)).where(User.license_type == "permanent")
    )
    permanent_licenses = permanent_licenses_q.scalar() or 0

    # Model call stats (last 24h)
    yesterday = today_start - timedelta(hours=24)
    model_calls_q = await db.execute(
        select(func.count(ModelMonitor.id)).where(ModelMonitor.created_at >= yesterday)
    )
    model_calls_24h = model_calls_q.scalar() or 0

    model_errors_q = await db.execute(
        select(func.count(ModelMonitor.id)).where(
            ModelMonitor.created_at >= yesterday,
            ModelMonitor.status == "error",
        )
    )
    model_errors_24h = model_errors_q.scalar() or 0
    error_rate = round(model_errors_24h / max(model_calls_24h, 1) * 100, 2)

    # Revenue (all time)
    revenue_q = await db.execute(
        select(func.coalesce(func.sum(Invoice.amount), 0)).where(
            Invoice.provider_status == "completed"
        )
    )
    total_revenue = round(revenue_q.scalar() or 0, 2)

    # Ad stats (today)
    ad_count_q = await db.execute(
        select(func.count(AdLog.id)).where(
            AdLog.created_at >= today_start,
            AdLog.action == "reward",
        )
    )
    ad_rewards_today = ad_count_q.scalar() or 0

    # Free tier users count
    free_users_q = await db.execute(
        select(func.count(User.id)).where(
            User.subscription_status == "free",
            User.license_type != "permanent",
        )
    )
    free_users = free_users_q.scalar() or 0

    return {
        "status": "ok",
        "overview": {
            "total_users": total_users,
            "free_users": free_users,
            "today_recognitions": today_recognitions,
            "weekly_recognitions": weekly_recognitions,
            "active_subscriptions": active_subscriptions,
            "permanent_licenses": permanent_licenses,
            "ad_rewards_today": ad_rewards_today,
            "model_calls_24h": model_calls_24h,
            "model_errors_24h": model_errors_24h,
            "error_rate_pct": error_rate,
            "total_revenue": total_revenue,
        },
    }


# ── User Management ──


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all users with subscription/license info."""
    offset = (page - 1) * page_size
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    total_q = await db.execute(select(func.count(User.id)))
    total = total_q.scalar() or 0

    return {
        "status": "ok",
        "total": total,
        "page": page,
        "page_size": page_size,
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "goal_type": u.goal_type,
                "subscription_status": u.subscription_status,
                "subscription_plan": u.subscription_plan,
                "license_type": u.license_type,
                "is_active": u.is_active,
                "daily_free_uses": u.daily_free_uses or 1,
                "ad_reward_credits": u.ad_reward_credits or 0,
                "remaining_recognitions": (u.remaining_daily_recognitions or 0) + (u.ad_reward_credits or 0),
                "created_at": u.created_at.isoformat() if u.created_at else "",
            }
            for u in users
        ],
    }


@router.post("/users/ban")
async def ban_user(
    target_user_id: str = Query(...),
    admin_id: str = Query("admin"),
    db: AsyncSession = Depends(get_db),
):
    """Ban/unban a user."""
    result = await db.execute(select(User).where(User.id == target_user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    user.is_active = not user.is_active
    await db.commit()

    # Audit log
    audit = AuditLog(
        id=_new_id(),
        admin_id=admin_id,
        action="ban_user" if not user.is_active else "unban_user",
        target_type="user",
        target_id=target_user_id,
        created_at=datetime.utcnow(),
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "ok",
        "user_id": target_user_id,
        "is_active": user.is_active,
    }


# ── Revenue ──


@router.get("/revenue")
async def revenue_stats(
    period: str = Query("monthly", pattern="^(daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_db),
):
    """Revenue breakdown by period."""
    now = datetime.utcnow()

    if period == "daily":
        since = now - timedelta(days=30)
        label = "近30天日收益"
    elif period == "weekly":
        since = now - timedelta(weeks=12)
        label = "近12周周收益"
    else:
        since = now - timedelta(days=365)
        label = "年收益"

    result = await db.execute(
        select(Invoice).where(
            Invoice.provider_status == "completed",
            Invoice.paid_at >= since,
        ).order_by(Invoice.paid_at)
    )
    invoices = result.scalars().all()

    # Breakdown by billing type
    sub_rev = sum(inv.amount for inv in invoices if inv.billing_type == "subscription")
    license_rev = sum(inv.amount for inv in invoices if inv.billing_type == "license")

    # Plan breakdown
    monthly_rev = sum(inv.amount for inv in invoices if inv.plan == "monthly")
    yearly_rev = sum(inv.amount for inv in invoices if inv.plan == "yearly")
    permanent_rev = sum(inv.amount for inv in invoices if inv.plan == "permanent")

    return {
        "status": "ok",
        "period": period,
        "label": label,
        "total_revenue": round(sum(inv.amount for inv in invoices), 2),
        "invoice_count": len(invoices),
        "breakdown": {
            "subscription": round(sub_rev, 2),
            "license": round(license_rev, 2),
        },
        "plan_breakdown": {
            "monthly": round(monthly_rev, 2),
            "yearly": round(yearly_rev, 2),
            "permanent": round(permanent_rev, 2),
        },
    }


# ── Model Monitor ──


@router.get("/model-monitor")
async def model_monitor(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Model usage, latency, error breakdown, and provider health status."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        select(ModelMonitor).where(ModelMonitor.created_at >= since).order_by(ModelMonitor.created_at.desc()).limit(1000)
    )
    logs = result.scalars().all()

    from collections import defaultdict
    model_stats = defaultdict(
        lambda: {"calls": 0, "errors": 0, "total_latency": 0.0, "total_tokens": 0.0, "failures": defaultdict(int)}
    )
    switch_events = []

    for log in logs:
        if log.status == "switch":
            switch_events.append({
                "id": log.id,
                "model_name": log.model_name,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else "",
            })
            continue

        ms = model_stats[log.model_name]
        ms["calls"] += 1
        if log.status == "error":
            ms["errors"] += 1
            # Classify failure reason
            err = log.error_message or ""
            if "503" in err or "http_503" in err:
                ms["failures"]["503"] += 1
            elif "429" in err or "http_429" in err:
                ms["failures"]["429"] += 1
            elif "timeout" in err.lower():
                ms["failures"]["timeout"] += 1
            elif "health" in err.lower():
                ms["failures"]["health_check"] += 1
            else:
                ms["failures"]["other"] += 1
        ms["total_latency"] += log.latency_ms
        ms["total_tokens"] += log.tokens_used

    # Import model_router health status
    from app.services.model_router import get_model_health_status, get_switch_events

    return {
        "status": "ok",
        "period_hours": hours,
        "total_calls": len(logs),
        "models": [
            {
                "name": name,
                "calls": stats["calls"],
                "errors": stats["errors"],
                "error_rate_pct": round(stats["errors"] / max(stats["calls"], 1) * 100, 2),
                "avg_latency_ms": round(stats["total_latency"] / max(stats["calls"], 1), 1),
                "total_tokens": stats["total_tokens"],
                "failure_breakdown": dict(stats["failures"]),
            }
            for name, stats in sorted(model_stats.items(), key=lambda x: -x[1]["calls"])
        ],
        "switch_events": switch_events[-20:],
        "provider_health": get_model_health_status(),
        "recent_switches": get_switch_events(limit=10),
    }


# ── System Config ──


@router.get("/config")
async def get_config(
    db: AsyncSession = Depends(get_db),
):
    """Get all system configuration keys."""
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    return {
        "status": "ok",
        "config": {c.key: c.value for c in configs},
    }


@router.post("/config")
async def update_config(
    key: str = Query(...),
    value: str = Query(""),
    admin_id: str = Query("admin"),
    db: AsyncSession = Depends(get_db),
):
    """Set a system configuration value."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()

    if config:
        config.value = value
        config.updated_by = admin_id
    else:
        config = SystemConfig(key=key, value=value, updated_by=admin_id)
        db.add(config)

    await db.commit()

    return {"status": "ok", "key": key, "value": value}


# ── Audit Logs ──


@router.get("/logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get security/audit logs."""
    offset = (page - 1) * page_size
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    )
    logs = result.scalars().all()

    return {
        "status": "ok",
        "count": len(logs),
        "page": page,
        "page_size": page_size,
        "logs": [
            {
                "id": log.id,
                "admin_id": log.admin_id,
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "details": log.details,
                "created_at": log.created_at.isoformat() if log.created_at else "",
            }
            for log in logs
        ],
    }


# ── Initialize default admin ──
async def init_default_admin(db: AsyncSession):
    """Create default admin user on first run."""
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == DEFAULT_ADMIN_USERNAME)
    )
    if not result.scalar_one_or_none():
        admin = AdminUser(
            id=_new_id(),
            username=DEFAULT_ADMIN_USERNAME,
            password_hash=_hash_password(DEFAULT_ADMIN_PASSWORD),
            role="super_admin",
            created_at=datetime.utcnow(),
        )
        db.add(admin)
        await db.commit()
