"""
Admin models — system configuration, admin users, RBAC, audit logs, and model monitoring.
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.db import Base


# ── RBAC: Association Tables ──

class Role(Base):
    """RBAC role definition."""
    __tablename__ = "roles"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, index=True)       # super_admin / admin / viewer
    description = Column(String, default="")
    is_system = Column(Boolean, default=False)            # cannot delete system roles
    created_at = Column(DateTime, default=datetime.utcnow)


class Permission(Base):
    """Granular permission definition."""
    __tablename__ = "permissions"

    id = Column(String, primary_key=True)
    code = Column(String, unique=True, index=True)        # user:read, system:monitor, billing:manage
    name = Column(String, default="")                      # Human-readable name
    group = Column(String, default="")                     # user / system / billing / content
    description = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class UserRole(Base):
    """Many-to-many: admin_user → roles."""
    __tablename__ = "user_roles"

    id = Column(String, primary_key=True)
    admin_id = Column(String, ForeignKey("admin_users.id", ondelete="CASCADE"), index=True)
    role_id = Column(String, ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RolePermission(Base):
    """Many-to-many: role → permissions."""
    __tablename__ = "role_permissions"

    id = Column(String, primary_key=True)
    role_id = Column(String, ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    permission_code = Column(String, ForeignKey("permissions.code", ondelete="CASCADE"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Existing Models (extended) ──

class AdminUser(Base):
    """Admin dashboard login credentials."""
    __tablename__ = "admin_users"

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="admin")          # legacy fallback — use RBAC roles via UserRole
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # RBAC: roles relationship
    roles = relationship("Role", secondary="user_roles",
                         primaryjoin="AdminUser.id == UserRole.admin_id",
                         secondaryjoin="Role.id == UserRole.role_id",
                         lazy="selectin")


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


# ── RBAC Seed Data ──

DEFAULT_PERMISSIONS = [
    # System
    {"code": "system:monitor", "name": "System Monitoring", "group": "system", "description": "View system metrics and monitoring"},
    {"code": "system:config", "name": "System Config", "group": "system", "description": "Manage system configuration"},
    {"code": "system:logs", "name": "Audit Logs", "group": "system", "description": "View audit logs"},
    # User management
    {"code": "user:read", "name": "User Read", "group": "user", "description": "View user list and details"},
    {"code": "user:manage", "name": "User Manage", "group": "user", "description": "Ban/unban users"},
    {"code": "user:delete", "name": "User Delete", "group": "user", "description": "Delete user accounts"},
    # Billing
    {"code": "billing:read", "name": "Billing Read", "group": "billing", "description": "View revenue and invoices"},
    {"code": "billing:manage", "name": "Billing Manage", "group": "billing", "description": "Manage billing and refunds"},
    # Content
    {"code": "content:read", "name": "Content Read", "group": "content", "description": "View meals and trends"},
    {"code": "content:moderate", "name": "Content Moderate", "group": "content", "description": "Moderate user content"},
    # AI / Models
    {"code": "ai:monitor", "name": "AI Monitor", "group": "ai", "description": "View model monitoring and usage"},
    {"code": "ai:configure", "name": "AI Configure", "group": "ai", "description": "Configure AI models and keys"},
    # Admin
    {"code": "admin:manage", "name": "Admin Manage", "group": "admin", "description": "Manage admin users and roles"},
    {"code": "admin:audit", "name": "Admin Audit", "group": "admin", "description": "View admin action audit trail"},
]

DEFAULT_ROLES = [
    {"id": "role_super_admin", "name": "super_admin", "description": "Full system access", "is_system": True,
     "permissions": [p["code"] for p in DEFAULT_PERMISSIONS]},
    {"id": "role_admin", "name": "admin", "description": "Administrative access", "is_system": True,
     "permissions": ["system:monitor", "system:config", "system:logs", "user:read", "user:manage", "billing:read", "billing:manage", "content:read", "content:moderate", "ai:monitor", "admin:audit"]},
    {"id": "role_viewer", "name": "viewer", "description": "Read-only access", "is_system": True,
     "permissions": ["system:monitor", "system:logs", "user:read", "billing:read", "content:read", "ai:monitor", "admin:audit"]},
]


async def _seed_rbac():
    """Seed default roles and permissions into the database."""
    from sqlalchemy import select
    from app.db import async_session

    async with async_session() as session:
        # Check if already seeded
        result = await session.execute(select(Permission).limit(1))
        if result.scalar_one_or_none():
            return  # Already seeded

        logger = logging.getLogger(__name__)

        # Insert permissions
        for p_data in DEFAULT_PERMISSIONS:
            perm = Permission(
                id=p_data["code"],
                code=p_data["code"],
                name=p_data["name"],
                group=p_data["group"],
                description=p_data["description"],
            )
            session.add(perm)
        logger.info(f"Seeded {len(DEFAULT_PERMISSIONS)} permissions")

        # Insert roles with permissions
        for r_data in DEFAULT_ROLES:
            role = Role(
                id=r_data["id"],
                name=r_data["name"],
                description=r_data["description"],
                is_system=r_data["is_system"],
            )
            session.add(role)

            # Create role-permission associations
            for perm_code in r_data["permissions"]:
                rp = RolePermission(
                    id=f"{r_data['id']}_{perm_code}",
                    role_id=r_data["id"],
                    permission_code=perm_code,
                )
                session.add(rp)
        logger.info(f"Seeded {len(DEFAULT_ROLES)} roles with permissions")

        await session.commit()


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
