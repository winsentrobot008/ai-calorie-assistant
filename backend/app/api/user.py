"""
User API — lightweight registration, profile management, and OAuth.
"""
import os
import uuid
import hashlib
import logging
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from jose import jwt as jose_jwt, jwk as jose_jwk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User

router = APIRouter(prefix="/api/v1", tags=["user"])

logger = logging.getLogger(__name__)

# ── JWT Config ──
JWT_SECRET = os.getenv("JWT_SECRET", "dev-jwt-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7

# ── OAuth Client IDs (set in .env) ──
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "")
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")


class OAuthTokenRequest(BaseModel):
    """Request body for OAuth login endpoints."""
    token: str
    user: dict = {}


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


@router.post("/user/login")
async def login(
    email: str = Query(...),
    password: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """Login with email + password. Returns user_id on success."""
    existing = await db.execute(select(User).where(User.email == email))
    user = existing.scalar_one_or_none()

    if not user:
        raise HTTPException(401, "Invalid email or password")

    if password and user.password_hash != _hash_password(password):
        raise HTTPException(401, "Invalid email or password")
    elif not password and user.password_hash:
        raise HTTPException(401, "Password required")

    return {
        "status": "ok",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
    }


@router.post("/user/register")
async def register(
    name: str = Query(""),
    email: str = Query(""),
    password: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """Register a new user (anonymous or email-based)."""
    # Check if email already exists
    if email:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise HTTPException(400, "Email already registered")

    user_id = _new_id()
    user = User(
        id=user_id,
        name=name or "User",
        email=email,
        password_hash=_hash_password(password) if password else "",
        goal_type="maintain",
        daily_calories=2000.0,
        daily_protein=60.0,
        daily_fat=65.0,
        daily_carbs=300.0,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()

    return {
        "status": "ok",
        "user_id": user_id,
        "name": user.name,
        "email": user.email,
    }


@router.get("/user/profile")
async def get_profile(
    user_id: str = Query("anonymous"),
    db: AsyncSession = Depends(get_db),
):
    """Get user profile and daily goals."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        # Return default profile for anonymous
        return {
            "status": "ok",
            "user": {
                "id": "anonymous",
                "name": "Anonymous",
                "email": "",
                "goal_type": "maintain",
                "daily_calories": 2000,
                "daily_protein": 60,
                "daily_fat": 65,
                "daily_carbs": 300,
            },
        }

    return {
        "status": "ok",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "goal_type": user.goal_type,
            "daily_calories": user.daily_calories,
            "daily_protein": user.daily_protein,
            "daily_fat": user.daily_fat,
            "daily_carbs": user.daily_carbs,
            "created_at": user.created_at.isoformat() if user.created_at else "",
        },
    }


@router.put("/user/profile")
async def update_profile(
    user_id: str = Query(...),
    name: str = Query(""),
    goal_type: str = Query(""),
    daily_calories: float = Query(0),
    daily_protein: float = Query(0),
    daily_fat: float = Query(0),
    daily_carbs: float = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile and daily goals."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    if name:
        user.name = name
    if goal_type:
        user.goal_type = goal_type
    if daily_calories > 0:
        user.daily_calories = daily_calories
    if daily_protein > 0:
        user.daily_protein = daily_protein
    if daily_fat > 0:
        user.daily_fat = daily_fat
    if daily_carbs > 0:
        user.daily_carbs = daily_carbs

    await db.commit()

    return {
        "status": "ok",
        "user": {
            "id": user.id,
            "name": user.name,
            "goal_type": user.goal_type,
            "daily_calories": user.daily_calories,
            "daily_protein": user.daily_protein,
            "daily_fat": user.daily_fat,
            "daily_carbs": user.daily_carbs,
        },
    }


# ═══════════════════════════════════════════════════
#  OAuth Helpers
# ═══════════════════════════════════════════════════

def create_jwt(user: User) -> str:
    """Create a JWT token for the given user."""
    expire = datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    payload = {
        "sub": user.id,
        "email": user.email,
        "name": user.name,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jose_jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_or_create_oauth_user(user_info: dict, db: AsyncSession) -> User:
    """Find existing user by email or create a new one for OAuth login."""
    email = user_info.get("email", "")
    name = user_info.get("name", "User")

    if email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            return user

    user_id = _new_id()
    user = User(
        id=user_id,
        name=name,
        email=email,
        password_hash="",
        goal_type="maintain",
        daily_calories=2000.0,
        daily_protein=60.0,
        daily_fat=65.0,
        daily_carbs=300.0,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ═══════════════════════════════════════════════════
#  OAuth Endpoints
# ═══════════════════════════════════════════════════

@router.post("/user/oauth/google")
async def google_oauth(body: OAuthTokenRequest, db: AsyncSession = Depends(get_db)):
    """Google OAuth — verify ID token via Google's tokeninfo endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": body.token},
                timeout=10,
            )
        if resp.status_code != 200:
            raise HTTPException(401, "Invalid Google token")
        info = resp.json()

        # Verify audience matches our client ID (if configured)
        if GOOGLE_CLIENT_ID and info.get("aud") != GOOGLE_CLIENT_ID:
            raise HTTPException(401, "Token audience mismatch")

        user = await get_or_create_oauth_user(
            {"email": info.get("email", ""), "name": info.get("name", info.get("given_name", "Google User"))},
            db,
        )
        jwt_token = create_jwt(user)

        return {
            "token": jwt_token,
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
        }
    except httpx.RequestError:
        raise HTTPException(502, "Failed to verify Google token")


@router.post("/user/oauth/apple")
async def apple_oauth(body: OAuthTokenRequest, db: AsyncSession = Depends(get_db)):
    """Apple OAuth — verify identity token with Apple's public JWK keys."""
    try:
        # Fetch Apple's public keys
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://appleid.apple.com/auth/keys", timeout=10)
        if resp.status_code != 200:
            raise HTTPException(502, "Failed to fetch Apple public keys")
        keys_data = resp.json()

        # Read token header to find the key ID
        unverified_header = jose_jwt.get_unverified_header(body.token)
        kid = unverified_header.get("kid")

        # Locate matching JWK
        matching_key = None
        for key in keys_data.get("keys", []):
            if key.get("kid") == kid:
                matching_key = key
                break
        if not matching_key:
            raise HTTPException(401, "Apple public key not found for token")

        public_key = jose_jwk.RSAKey.import_key(matching_key)

        # Verify and decode the identity token
        payload = jose_jwt.decode(
            body.token,
            public_key,
            algorithms=["RS256"],
            audience=APPLE_CLIENT_ID if APPLE_CLIENT_ID else None,
            options={"verify_aud": bool(APPLE_CLIENT_ID)},
        )

        # Apple sends user info only on first registration
        apple_user = body.user or {}
        user_info = {
            "email": payload.get("email", ""),
            "name": apple_user.get("name", payload.get("name", "")),
        }

        user = await get_or_create_oauth_user(user_info, db)
        jwt_token = create_jwt(user)

        return {
            "token": jwt_token,
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, f"Invalid Apple token: {str(e)}")


@router.post("/user/oauth/facebook")
async def facebook_oauth():
    """Facebook OAuth — 已临时禁用 (2026-07-24)."""
    raise HTTPException(status_code=501, detail="Facebook login is temporarily disabled")


# ═══════════════════════════════════════════════════
#  Facebook OAuth — Authorization Code Flow
# ═══════════════════════════════════════════════════

auth_router = APIRouter(tags=["oauth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@auth_router.get("/auth/facebook/login")
async def facebook_login():
    """Facebook OAuth login — 已临时禁用 (2026-07-24)."""
    raise HTTPException(status_code=501, detail="Facebook login is temporarily disabled")


@auth_router.get("/auth/facebook/callback")
async def facebook_callback():
    """Facebook OAuth callback — 已临时禁用 (2026-07-24)."""
    raise HTTPException(status_code=501, detail="Facebook login is temporarily disabled")
