"""
Model Router Service — health checks, auto-switch with retry, fallback chain.

Provider priority:
  1. DeepSeek (primary)   —  AI vision / nutrition / suggestion
  2. HuggingFace (backup) —  food101 classifier
  3. Local fallback       —  built-in food DB / rule-based suggestions

Health check:
  - Lightweight ping before each primary call (2s timeout)
  - If ping fails or status >= 500 → retry once immediately (1s budget)
  - If retry fails → switch to next provider

Logging:
  - All calls logged to ModelMonitor table
  - Switch events persisted to ModelMonitor with "switch" status
  - Consecutive failure counter for alerting
"""
import os
import time
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

# ── Configuration ──
HEALTH_CHECK_TIMEOUT = 2.0           # seconds
RETRY_BUDGET = 1.0                   # retry must complete within 1s
CONSECUTIVE_FAILURE_ALERT = 3        # alert after N consecutive failures

# ── In-memory health state ──
_model_health = {
    "deepseek":   {"healthy": True, "consecutive_failures": 0, "last_failure_reason": ""},
    "huggingface":{"healthy": True, "consecutive_failures": 0, "last_failure_reason": ""},
}
_switch_events: list[dict] = []


# ── Helpers ──

def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# ── Health Checks ──

async def _health_check_deepseek() -> tuple[bool, str]:
    """Ping DeepSeek (OpenAI-compatible) models list — lightweight, <2s."""
    api_key = _env("AI_API_KEY")
    base_url = _env("AI_API_BASE_URL", "https://api.lk888.ai")
    if not api_key:
        return False, "no_api_key"
    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        elapsed_ms = (time.monotonic() - start) * 1000
        if resp.status_code >= 500:
            return False, f"http_{resp.status_code}"
        if elapsed_ms > HEALTH_CHECK_TIMEOUT * 1000:
            return False, "timeout"
        return True, ""
    except httpx.TimeoutException:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:60]


async def _health_check_hf() -> tuple[bool, str]:
    """Ping HuggingFace Inference API — HEAD request."""
    try:
        async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
            resp = await client.head(
                f"https://api-inference.huggingface.co/models/{_env('HF_MODEL', 'nateraw/food101')}",
            )
        if resp.status_code >= 500:
            return False, f"http_{resp.status_code}"
        return True, ""
    except Exception as e:
        return False, str(e)[:60]


async def check_health(provider: str) -> tuple[bool, str]:
    """Check if a provider is healthy. Returns (healthy, reason)."""
    if provider == "deepseek":
        return await _health_check_deepseek()
    elif provider == "huggingface":
        return await _health_check_hf()
    return True, ""


# ── Error Classification ──

def classify_error(status_code: int, error_msg: str) -> str:
    """Map error to category for monitoring dashboard."""
    err_lower = (error_msg or "").lower()
    if status_code == 503 or "503" in err_lower:
        return "503"
    if status_code == 429 or "429" in err_lower:
        return "429"
    if "timeout" in err_lower:
        return "timeout"
    if status_code >= 500:
        return "5xx"
    return "other"


# ── DB Logging ──

async def log_model_call(
    db_session,
    model_name: str,
    endpoint: str,
    latency_ms: float,
    status: str,
    error_message: str = "",
    tokens_used: float = 0,
    user_id: str = "",
):
    """Record a model call to ModelMonitor table."""
    from app.models.admin import ModelMonitor
    import uuid
    monitor = ModelMonitor(
        id=uuid.uuid4().hex[:12],
        model_name=model_name,
        endpoint=endpoint,
        latency_ms=round(latency_ms, 1),
        status=status,
        error_message=(error_message or "")[:200],
        tokens_used=tokens_used,
        user_id=user_id,
        created_at=datetime.utcnow(),
    )
    db_session.add(monitor)
    await db_session.commit()


async def log_switch_event(
    db_session,
    from_provider: str,
    to_provider: str,
    reason: str,
):
    """Log a provider switch event (both in-memory and DB)."""
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "from": from_provider,
        "to": to_provider,
        "reason": reason,
    }
    _switch_events.append(event)
    if len(_switch_events) > 100:
        _switch_events.pop(0)

    logger.warning("MODEL SWITCH: %s → %s (reason: %s)", from_provider, to_provider, reason)

    # Persist to DB as a special ModelMonitor entry
    from app.models.admin import ModelMonitor
    import uuid
    monitor = ModelMonitor(
        id=uuid.uuid4().hex[:12],
        model_name=f"switch:{from_provider}→{to_provider}",
        endpoint="switch",
        latency_ms=0,
        status="switch",
        error_message=(reason or "")[:200],
        user_id="system",
        created_at=datetime.utcnow(),
    )
    db_session.add(monitor)
    await db_session.commit()


# ── Public Query APIs ──

def get_switch_events(limit: int = 20) -> list[dict]:
    """Return recent switch events (newest first)."""
    return list(reversed(_switch_events[-limit:]))


def get_model_health_status() -> dict:
    """Return current in-memory health for all providers."""
    return dict(_model_health)


# ── Core: call_with_fallback ──

async def call_with_fallback(
    db_session,
    provider_calls: list[dict],
    user_id: str = "",
    endpoint: str = "",
    skip_health_check: bool = False,
) -> tuple:
    """
    Try providers in order with health check + retry.

    Args:
        db_session: SQLAlchemy async session for logging
        provider_calls: List of dicts:
            - "provider": "deepseek" | "huggingface" | "fallback"
            - "call": async callable → (result, latency_ms, status, error_msg, tokens)
        user_id: User ID for logging
        endpoint: API endpoint name for logging
        skip_health_check: Skip health ping (use when provider selection already done)

    Returns:
        (result, provider_used, switched, error_info)
        - result: the return value from the successful call
        - provider_used: which provider succeeded ("deepseek"|"huggingface"|"fallback"|"none")
        - switched: True if a fallback was triggered
        - error_info: str with last error if all failed
    """
    last_error = ""
    switched = False

    for idx, entry in enumerate(provider_calls):
        provider = entry["provider"]
        call_fn = entry["call"]

        # Detect switch
        if idx > 0:
            switched = True
            await log_switch_event(
                db_session,
                from_provider=provider_calls[idx - 1]["provider"],
                to_provider=provider,
                reason=f"previous_failed:{last_error[:100]}",
            )

        # Fallback — no health check, no retry
        if provider == "fallback":
            try:
                result = await call_fn()
                await log_model_call(db_session, "fallback", endpoint, 0, "success", user_id=user_id)
                return result, provider, switched, ""
            except Exception as e:
                logger.error("Fallback also failed: %s", e)
                return None, "none", switched, str(e)[:200]

        # ── Health check ──
        if not skip_health_check:
            healthy, reason = await check_health(provider)
            if not healthy:
                logger.warning("%s health check FAILED: %s", provider, reason)
                _update_health(provider, reason)

                await log_model_call(
                    db_session, provider, f"{endpoint}/health", 0, "error",
                    error_message=f"health:{reason}", user_id=user_id,
                )

                # Immediate retry (fast path — 1s budget)
                retry_ok, retry_result = await _do_retry(db_session, call_fn, provider, endpoint, user_id)
                if retry_ok:
                    return retry_result, provider, switched, ""
                last_error = f"health:{reason}"
                continue  # next provider

        # ── Primary call ──
        call_start = time.monotonic()
        try:
            result, latency, status, err_msg, tokens = await call_fn()
        except Exception as e:
            elapsed_ms = (time.monotonic() - call_start) * 1000
            last_error = str(e)[:200]
            _update_health(provider, last_error)
            await log_model_call(db_session, provider, endpoint, elapsed_ms, "error",
                                 error_message=last_error, user_id=user_id)

            # Retry
            retry_ok, retry_result = await _do_retry(db_session, call_fn, provider, endpoint, user_id)
            if retry_ok:
                return retry_result, provider, switched, ""
            continue

        # ── Handle HTTP status ──
        elapsed_ms = (time.monotonic() - call_start) * 1000
        if status == "success":
            _model_health.get(provider, {})["consecutive_failures"] = 0
            await log_model_call(db_session, provider, endpoint, elapsed_ms, "success",
                                 tokens_used=tokens, user_id=user_id)
            return result, provider, switched, ""
        else:
            last_error = err_msg or f"http_{status}"
            _update_health(provider, last_error)
            await log_model_call(db_session, provider, endpoint, elapsed_ms, "error",
                                 error_message=last_error, user_id=user_id)

            # Alert check
            if _model_health.get(provider, {}).get("consecutive_failures", 0) >= CONSECUTIVE_FAILURE_ALERT:
                logger.error("*** ALERT: %s consecutive failures for %s! ***",
                             CONSECUTIVE_FAILURE_ALERT, provider)

            # Retry
            retry_ok, retry_result = await _do_retry(db_session, call_fn, provider, endpoint, user_id)
            if retry_ok:
                return retry_result, provider, switched, ""
            continue

    return None, "none", switched, last_error


async def _do_retry(db_session, call_fn, provider: str, endpoint: str, user_id: str) -> tuple[bool, any]:
    """Attempt one immediate retry. Returns (success, result)."""
    retry_start = time.monotonic()
    try:
        result, latency, status, err_msg, tokens = await call_fn()
        elapsed_ms = (time.monotonic() - retry_start) * 1000
        if status == "success":
            _model_health.get(provider, {})["consecutive_failures"] = 0
            await log_model_call(db_session, provider, f"{endpoint}/retry", elapsed_ms, "success",
                                 tokens_used=tokens, user_id=user_id)
            return True, result
        else:
            await log_model_call(db_session, provider, f"{endpoint}/retry", elapsed_ms, "error",
                                 error_message=err_msg or f"retry_failed:{status}", user_id=user_id)
            return False, None
    except Exception as e:
        elapsed_ms = (time.monotonic() - retry_start) * 1000
        await log_model_call(db_session, provider, f"{endpoint}/retry", elapsed_ms, "error",
                             error_message=str(e)[:200], user_id=user_id)
        return False, None


def _update_health(provider: str, reason: str):
    """Update in-memory health state."""
    if provider in _model_health:
        _model_health[provider]["consecutive_failures"] += 1
        _model_health[provider]["last_failure_reason"] = reason
        _model_health[provider]["healthy"] = False
