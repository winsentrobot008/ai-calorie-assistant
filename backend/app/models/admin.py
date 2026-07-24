"""
Admin models — system configuration, admin users, and audit logs.
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, JSON
from app.db import Base


class AdminUser(Base):
    """Admin dashboard login credentials."""
    __tablename__ = "admin_users"

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="admin")          # super_admin / admin / viewer
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemConfig(Base):
    """Dynamic system configuration key-value store."""
    __tablename__ = "system_config"

    key = Column(String, primary_key=True)
    value = Column(Text, default="")
    description = Column(String, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String, default="system")


class AuditLog(Base):
    """Security audit log for admin actions."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True)
    admin_id = Column(String, index=True)
    action = Column(String)                        # update_config / ban_user / refund
    target_type = Column(String, default="")       # user / config / invoice
    target_id = Column(String, default="")
    details = Column(JSON, default=dict)
    ip_address = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelMonitor(Base):
    """AI model call monitoring — tracks usage, latency, and errors per model."""
    __tablename__ = "model_monitor"

    id = Column(String, primary_key=True)
    model_name = Column(String, index=True)        # deepseek-chat / hf-food101
    endpoint = Column(String, default="")           # /api/v1/meals/analyze-image
    latency_ms = Column(Float, default=0.0)
    status = Column(String, default="success")      # success / error / timeout
    error_message = Column(String, default="")
    tokens_used = Column(Float, default=0.0)
    user_id = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
