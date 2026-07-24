"""
AI Calorie Assistant — FastAPI entry point.
"""
import os
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Logging Configuration ──
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
logger.info(f"Log level set to {LOG_LEVEL}")

from app.db import init_db, async_session
from app.api.meals import router as meals_router
from app.api.stats import router as stats_router
from app.api.user import router as user_router, auth_router as oauth_router
from app.api.insight import router as insight_router
from app.api.billing import router as billing_router
from app.api.admin import router as admin_router, init_default_admin
from app.api.ads import router as ads_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Create default admin user
    async with async_session() as session:
        await init_default_admin(session)
    yield


app = FastAPI(title="AI Calorie Assistant", version="0.1.0", lifespan=lifespan)

# ── CORS: allow_origins from env (production overrides dev default) ──
raw_origins = os.getenv("ALLOW_ORIGINS", "")
if raw_origins:
    try:
        allow_origins = json.loads(raw_origins)
    except json.JSONDecodeError:
        allow_origins = ["*"]
        logger.warning(f"Invalid ALLOW_ORIGINS JSON: {raw_origins}, falling back to ['*']")
else:
    allow_origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving
os.makedirs("storage/uploads", exist_ok=True)
os.makedirs("storage/downloads", exist_ok=True)
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# Register routers
app.include_router(meals_router)
app.include_router(stats_router)
app.include_router(user_router)
app.include_router(oauth_router)
app.include_router(insight_router)
app.include_router(billing_router)
app.include_router(admin_router)
app.include_router(ads_router)


@app.get("/health")
async def health():
    return {"status": "ok", "project": "AI Calorie Assistant"}


@app.get("/healthz")
async def healthz():
    """Kubernetes-style health check endpoint."""
    return {"status": "ok"}
