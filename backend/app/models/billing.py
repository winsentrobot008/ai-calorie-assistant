"""
Billing models — invoices, transactions, and payment records.
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text
from app.db import Base


class Invoice(Base):
    """Payment invoice / transaction record."""
    __tablename__ = "invoices"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, default="anonymous")
    email = Column(String, default="")

    # Payment provider info
    provider = Column(String, default="stripe")        # stripe / paypal / wechat
    provider_invoice_id = Column(String, default="")
    provider_status = Column(String, default="pending")  # pending / completed / failed / refunded

    # Billing details
    amount = Column(Float, default=0.0)
    currency = Column(String, default="usd")
    plan = Column(String, default="")                   # monthly / yearly / permanent
    billing_type = Column(String, default="subscription") # subscription / license

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class AdLog(Base):
    """Advertisement impression / click tracking."""
    __tablename__ = "ad_logs"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, default="anonymous")
    ad_type = Column(String, default="banner")           # banner / sidebar / interstitial
    action = Column(String, default="impression")        # impression / click
    ip_address = Column(String, default="")
    user_agent = Column(String, default="")
    page_url = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
