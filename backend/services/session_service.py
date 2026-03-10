"""
Redis-backed session service.

Stores per-session state: thread_id (LangGraph), customer_id, message count,
and creation timestamp. Falls back to in-memory dict when Redis is unavailable
so development works without Redis running.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _make_session_key(session_id: str) -> str:
    return f"techhub:session:{session_id}"


def _make_thread_key(session_id: str) -> str:
    return f"techhub:thread:{session_id}"


# ---------------------------------------------------------------------------
# Fallback in-memory store (used when Redis is not available)
# ---------------------------------------------------------------------------
_memory_store: dict[str, dict] = {}


def _get_redis_client():
    """Return a Redis client or None if Redis is unavailable."""
    try:
        import redis
        import os

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1)
        client.ping()  # fail fast if Redis is down
        return client
    except Exception:
        logger.warning("Redis unavailable — using in-memory session store")
        return None


_redis = _get_redis_client()

# Session TTL: 24 hours
SESSION_TTL = 60 * 60 * 24


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_session() -> str:
    """Create a new session and return its session_id."""
    session_id = str(uuid.uuid4())
    thread_id = str(uuid.uuid4())  # LangGraph thread ID (unique per session)

    data = {
        "session_id": session_id,
        "thread_id": thread_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message_count": 0,
        "customer_id": "",
    }

    _save(session_id, data)
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """Return session data dict or None if not found."""
    return _load(session_id)


def get_thread_id(session_id: str) -> Optional[str]:
    """Return the LangGraph thread_id for a session."""
    data = _load(session_id)
    return data["thread_id"] if data else None


def increment_message_count(session_id: str) -> None:
    """Increment the message counter for a session."""
    data = _load(session_id)
    if data:
        data["message_count"] = data.get("message_count", 0) + 1
        _save(session_id, data)


def set_customer_id(session_id: str, customer_id: str) -> None:
    """Persist the verified customer_id in the session."""
    data = _load(session_id)
    if data:
        data["customer_id"] = customer_id
        _save(session_id, data)


def session_exists(session_id: str) -> bool:
    return _load(session_id) is not None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _save(session_id: str, data: dict) -> None:
    if _redis:
        _redis.setex(_make_session_key(session_id), SESSION_TTL, json.dumps(data))
    else:
        _memory_store[session_id] = data


def _load(session_id: str) -> Optional[dict]:
    if _redis:
        raw = _redis.get(_make_session_key(session_id))
        return json.loads(raw) if raw else None
    return _memory_store.get(session_id)
