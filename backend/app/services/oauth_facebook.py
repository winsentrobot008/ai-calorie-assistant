"""
Facebook OAuth service — server-side authorization code flow.

Flow:
  1. Frontend redirects user to /auth/facebook/login
  2. Backend redirects to Facebook OAuth dialog
  3. User authorizes → Facebook redirects to /auth/facebook/callback?code=xxx
  4. Backend exchanges code for access token
  5. Backend fetches user info from Graph API
  6. Auto-create or auto-login → issue JWT → redirect frontend with token
"""

import os
import logging
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
FACEBOOK_REDIRECT_URI = os.getenv(
    "FACEBOOK_REDIRECT_URI",
    "http://localhost:8001/auth/facebook/callback",
)

AUTHORIZATION_URL = "https://www.facebook.com/v18.0/dialog/oauth"
TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
GRAPH_API_URL = "https://graph.facebook.com/v18.0/me"


def get_login_url(state: str = "") -> str:
    """Generate Facebook OAuth authorization URL.

    Args:
        state: Optional CSRF state parameter.

    Returns:
        Full Facebook OAuth dialog URL.
    """
    params = {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": FACEBOOK_REDIRECT_URI,
        "scope": "public_profile,email",
        "response_type": "code",
    }
    if state:
        params["state"] = state
    return f"{AUTHORIZATION_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> str:
    """Exchange authorization code for a long-lived access token.

    Args:
        code: The authorization code from Facebook callback.

    Returns:
        Access token string.

    Raises:
        ValueError: If token exchange fails.
    """
    params = {
        "client_id": FACEBOOK_APP_ID,
        "client_secret": FACEBOOK_APP_SECRET,
        "redirect_uri": FACEBOOK_REDIRECT_URI,
        "code": code,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(TOKEN_URL, params=params, timeout=10)
    if resp.status_code != 200:
        logger.error("Facebook token exchange failed: %s %s", resp.status_code, resp.text)
        raise ValueError(f"Token exchange failed: HTTP {resp.status_code}")
    data = resp.json()
    if "access_token" not in data:
        logger.error("Facebook token exchange: no access_token in response: %s", data)
        raise ValueError("No access_token in response")
    logger.info("Facebook token exchange succeeded (expires: %s)", data.get("expires_in"))
    return data["access_token"]


async def get_user_info(access_token: str) -> dict:
    """Fetch user profile from Facebook Graph API.

    Args:
        access_token: Valid Facebook access token.

    Returns:
        User info dict with id, name, email, picture fields.
    """
    params = {
        "access_token": access_token,
        "fields": "id,name,email,picture",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(GRAPH_API_URL, params=params, timeout=10)
    if resp.status_code != 200:
        logger.error("Facebook Graph API failed: %s %s", resp.status_code, resp.text)
        raise ValueError(f"Graph API failed: HTTP {resp.status_code}")
    return resp.json()
