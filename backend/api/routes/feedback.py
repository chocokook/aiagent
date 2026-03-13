"""
Feedback route.

POST /feedback — submit satisfaction score and resolution status after a conversation.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.metrics import (
    feedback_resolved_total,
    feedback_unresolved_total,
    first_contact_resolved_total,
    satisfaction_score_count,
    satisfaction_score_sum,
)
from backend.services import get_session

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    session_id: str
    resolved: bool
    score: int = Field(..., ge=1, le=5)


@router.post("")
async def submit_feedback(req: FeedbackRequest):
    if req.resolved:
        feedback_resolved_total.inc()
        # First-contact resolution: user sent exactly 1 message and issue resolved
        session = get_session(req.session_id)
        if session and session.get("message_count", 0) == 1:
            first_contact_resolved_total.inc()
    else:
        feedback_unresolved_total.inc()

    satisfaction_score_sum.inc(req.score)
    satisfaction_score_count.inc()

    return {"ok": True}
