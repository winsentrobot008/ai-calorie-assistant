"""
Billing API — subscription management, license purchases, ad rewards, and billing.
"""
import uuid
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User, reset_daily_free_uses
from app.models.billing import Invoice, AdLog

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


# ── Pricing Plans ──
PLANS = {
    "monthly": {"price": 9.99, "currency": "usd", "label": "月付", "days": 30},
    "yearly": {"price": 79.99, "currency": "usd", "label": "年付", "days": 365},
    "permanent": {"price": 199.00, "currency": "usd", "label": "永久买断", "days": None},
}

FREE_TIER_LIMITS = {
    "daily_free_uses": 1,
    "ad_reward_per_video": 1,       # 每次看广告获得 1 次识别
    "max_ad_credits": 10,            # 广告积分上限
}


def _is_premium(user) -> bool:
    """Check if user has premium access (subscription or permanent)."""
    now = datetime.utcnow()
    return (
        (user.subscription_status == "active" and user.subscription_expiry and user.subscription_expiry > now)
    ) or user.license_type == "permanent"


# ── Stripe Webhook ──
@router.post("/stripe-webhook")
async def stripe_webhook(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Stripe webhook endpoint for subscription lifecycle events.
    Supports: checkout.session.completed, invoice.paid, customer.subscription.deleted
    """
    event_type = payload.get("type", "")
    data = payload.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        customer_id = data.get("customer", "")
        user_id = data.get("client_reference_id", "")
        subscription_id = data.get("subscription", "")

        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.stripe_customer_id = customer_id
                user.stripe_subscription_id = subscription_id
                user.subscription_status = "active"
                # Infer plan from metadata or default to monthly
                plan = data.get("metadata", {}).get("plan", "monthly")
                plan_info = PLANS.get(plan, PLANS["monthly"])
                user.subscription_plan = plan
                user.subscription_expiry = datetime.utcnow() + timedelta(days=plan_info["days"])
                await db.commit()

    elif event_type == "invoice.paid":
        subscription_id = data.get("subscription", "")
        if subscription_id:
            result = await db.execute(
                select(User).where(User.stripe_subscription_id == subscription_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.subscription_status = "active"
                # Extend expiry by 30/365 days from current expiry
                plan_info = PLANS.get(user.subscription_plan, PLANS["monthly"])
                current_expiry = user.subscription_expiry or datetime.utcnow()
                new_expiry = max(current_expiry, datetime.utcnow()) + timedelta(days=plan_info["days"])
                user.subscription_expiry = new_expiry

                # Create invoice record
                invoice = Invoice(
                    id=_new_id(),
                    user_id=user.id,
                    email=user.email,
                    provider="stripe",
                    provider_invoice_id=data.get("id", ""),
                    provider_status="completed",
                    amount=data.get("amount_paid", 0) / 100,
                    currency=data.get("currency", "usd"),
                    plan=user.subscription_plan,
                    billing_type="subscription",
                    created_at=datetime.utcnow(),
                    paid_at=datetime.utcnow(),
                    expires_at=new_expiry,
                )
                db.add(invoice)
                await db.commit()

    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id", "")
        if subscription_id:
            result = await db.execute(
                select(User).where(User.stripe_subscription_id == subscription_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.subscription_status = "expired"
                await db.commit()

    return {"status": "ok", "event": event_type}


# ── Plans ──
@router.get("/plans")
async def get_plans():
    """Return available pricing plans and free tier info."""
    return {
        "status": "ok",
        "plans": PLANS,
        "free_limits": FREE_TIER_LIMITS,
    }


# ── Billing Status ──
@router.get("/status")
async def billing_status(
    user_id: str = Query("anonymous"),
    db: AsyncSession = Depends(get_db),
):
    """Get user's current billing/subscription status with free tier info."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(id=user_id, name=user_id)
        db.add(user)
        await db.commit()

    # Daily reset check
    reset_daily_free_uses(user)

    now = datetime.utcnow()
    is_active_sub = (
        user.subscription_status == "active"
        and user.subscription_expiry
        and user.subscription_expiry > now
    )
    is_permanent = user.license_type == "permanent"

    return {
        "status": "ok",
        "user_id": user.id,
        "email": user.email,
        "subscription_status": user.subscription_status,
        "subscription_plan": user.subscription_plan,
        "subscription_expiry": user.subscription_expiry.isoformat() if user.subscription_expiry else None,
        "license_type": user.license_type,
        "license_purchased_at": user.license_purchased_at.isoformat() if user.license_purchased_at else None,
        "daily_free_uses": user.daily_free_uses,
        "daily_free_date": user.daily_free_date,
        "ad_reward_credits": user.ad_reward_credits or 0,
        "remaining_daily_recognitions": user.remaining_daily_recognitions,
        "is_premium": bool(is_active_sub),
        "is_permanent": is_permanent,
    }


# ── Ad Reward — 已临时禁用 (2026-07-24) ──
@router.post("/ad-reward")
async def ad_reward():
    """
    Grant ad reward credits after watching a rewarded video.
    已临时禁用 — 见 restore_ad_rewards.patch 恢复。
    """
    raise HTTPException(
        status_code=501,
        detail={"status": "disabled", "message": "Ad rewards temporarily disabled"},
    )


# ── Subscribe ──
@router.post("/subscribe")
async def create_subscription(
    user_id: str = Query(...),
    plan: str = Query(..., pattern="^(monthly|yearly)$"),
    provider: str = Query("stripe"),
    provider_token: str = Query(""),       # payment nonce / token from frontend
    db: AsyncSession = Depends(get_db),
):
    """Create a new subscription (simulated or Stripe-based payment)."""
    if plan not in PLANS:
        raise HTTPException(400, f"Invalid plan: {plan}")

    plan_info = PLANS[plan]
    if plan_info["days"] is None:
        raise HTTPException(400, "Use /billing/license for permanent purchase")

    # Get or create user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found. Please register first.")

    # Simulate payment verification
    if not provider_token:
        payment_success = True
    else:
        payment_success = True  # In production: call Stripe/PayPal API

    if not payment_success:
        raise HTTPException(402, "Payment verification failed")

    now = datetime.utcnow()
    expiry = now + timedelta(days=plan_info["days"])

    # Update user
    user.subscription_status = "active"
    user.subscription_plan = plan
    user.subscription_expiry = expiry
    user.ad_reward_credits = 0  # Premium users don't need ad credits

    # Create invoice
    invoice = Invoice(
        id=_new_id(),
        user_id=user_id,
        email=user.email,
        provider=provider,
        provider_status="completed",
        amount=plan_info["price"],
        currency=plan_info["currency"],
        plan=plan,
        billing_type="subscription",
        created_at=now,
        paid_at=now,
        expires_at=expiry,
    )
    db.add(invoice)
    await db.commit()

    return {
        "status": "ok",
        "message": f"订阅成功！有效期至 {expiry.strftime('%Y-%m-%d')}",
        "subscription_status": "active",
        "subscription_plan": plan,
        "subscription_expiry": expiry.isoformat(),
        "invoice_id": invoice.id,
    }


# ── License (Permanent Buyout) ──
@router.post("/license")
async def purchase_license(
    user_id: str = Query(...),
    provider: str = Query("stripe"),
    provider_token: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """Purchase a permanent license (one-time buyout)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found. Please register first.")

    if user.license_type == "permanent":
        return {"status": "ok", "message": "您已拥有永久买断授权", "license_type": "permanent"}

    # Simulate payment verification
    if not provider_token:
        payment_success = True
    else:
        payment_success = True

    if not payment_success:
        raise HTTPException(402, "Payment verification failed")

    now = datetime.utcnow()
    plan_info = PLANS["permanent"]

    # Update user
    user.license_type = "permanent"
    user.license_purchased_at = now
    user.ad_reward_credits = 0  # Permanent users don't need ad credits

    # Create invoice
    invoice = Invoice(
        id=_new_id(),
        user_id=user_id,
        email=user.email,
        provider=provider,
        provider_status="completed",
        amount=plan_info["price"],
        currency=plan_info["currency"],
        plan="permanent",
        billing_type="license",
        created_at=now,
        paid_at=now,
    )
    db.add(invoice)
    await db.commit()

    return {
        "status": "ok",
        "message": "🎉 永久买断成功！所有功能已解锁",
        "license_type": "permanent",
        "invoice_id": invoice.id,
    }


# ── Cancel Subscription ──
@router.post("/cancel")
async def cancel_subscription(
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Cancel active subscription (stays active until expiry)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or user.subscription_status != "active":
        raise HTTPException(400, "No active subscription to cancel")

    user.subscription_status = "cancelled"
    await db.commit()

    return {
        "status": "ok",
        "message": "订阅已取消，服务将持续至有效期结束",
        "subscription_status": "cancelled",
        "subscription_expiry": user.subscription_expiry.isoformat() if user.subscription_expiry else None,
    }


# ── Invoices ──
@router.get("/invoices")
async def list_invoices(
    user_id: str = Query("anonymous"),
    db: AsyncSession = Depends(get_db),
):
    """List user's invoice/payment history."""
    result = await db.execute(
        select(Invoice)
        .where(Invoice.user_id == user_id)
        .order_by(Invoice.created_at.desc())
        .limit(50)
    )
    invoices = result.scalars().all()

    return {
        "status": "ok",
        "count": len(invoices),
        "invoices": [
            {
                "id": inv.id,
                "amount": inv.amount,
                "currency": inv.currency,
                "plan": inv.plan,
                "billing_type": inv.billing_type,
                "provider_status": inv.provider_status,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }
            for inv in invoices
        ],
    }
