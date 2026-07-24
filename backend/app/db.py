"""
Database setup — SQLite + SQLAlchemy async.
Auto-switches between dev and prod based on DATABASE_URL env var.
"""
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

DB_DIR = "storage"
os.makedirs(DB_DIR, exist_ok=True)

# ── Database URL: use DATABASE_URL env var if set (production), else dev default ──
DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    DATABASE_URL = f"sqlite+aiosqlite:///{DB_DIR}/calories.db"
    logger.info(f"Using dev database: {DATABASE_URL}")
else:
    logger.info(f"Using database: {DATABASE_URL}")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        from app.models.user import User
        from app.models.meal import Meal
        from app.models.trend import TrendCache, Suggestion
        from app.models.billing import Invoice, AdLog
        from app.models.admin import AdminUser, SystemConfig, AuditLog, ModelMonitor
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
