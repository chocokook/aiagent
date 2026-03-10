"""
Session management routes.

GET /sessions/{session_id} — fetch session metadata
DELETE /sessions/{session_id} — delete a session
"""

from fastapi import APIRouter, HTTPException

from backend.models import SessionInfo
from backend.services import get_session, session_exists

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """Return metadata for an existing session."""
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    data = get_session(session_id)
    return SessionInfo(
        session_id=data["session_id"],
        created_at=data["created_at"],
        message_count=data["message_count"],
        customer_id=data.get("customer_id") or None,
    )
