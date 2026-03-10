"""
Chat API routes.

POST /chat        — start or continue a conversation
POST /chat/resume — resume a HITL-interrupted conversation
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.models import ChatRequest, ChatResponse, ResumeRequest
from backend.services import (
    create_session,
    get_thread_id,
    increment_message_count,
    invoke_agent,
    resume_agent,
    session_exists,
    stream_agent,
    stream_resume_agent,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Send a message to the TechHub support agent.

    - If `session_id` is omitted a new session is created automatically.
    - Set `stream=true` to receive a streaming SSE response instead.
    """
    # Resolve or create session
    if req.session_id and session_exists(req.session_id):
        session_id = req.session_id
    else:
        session_id = create_session()

    thread_id = get_thread_id(session_id)
    if thread_id is None:
        raise HTTPException(status_code=500, detail="Failed to resolve thread_id")

    increment_message_count(session_id)

    # --- Streaming ---
    if req.stream:
        async def event_stream():
            # Prepend session_id as first event so the client can save it
            yield f"data: [SESSION] {session_id}\n\n"
            async for chunk in stream_agent(thread_id, req.message):
                yield chunk

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # --- Non-streaming ---
    result = invoke_agent(thread_id, req.message)
    return ChatResponse(
        session_id=session_id,
        message=result["content"],
        interrupted=result["interrupted"],
        interrupt_prompt=result["interrupt_prompt"],
    )


# ---------------------------------------------------------------------------
# POST /chat/resume
# ---------------------------------------------------------------------------


@router.post("/resume", response_model=ChatResponse)
async def resume_chat(req: ResumeRequest):
    """
    Provide a response to a HITL interrupt (e.g. supply email address).

    The `session_id` must belong to a previously interrupted conversation.
    """
    if not session_exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    thread_id = get_thread_id(req.session_id)
    if thread_id is None:
        raise HTTPException(status_code=500, detail="Failed to resolve thread_id")

    increment_message_count(req.session_id)

    # --- Streaming ---
    if req.stream:
        async def event_stream():
            async for chunk in stream_resume_agent(thread_id, req.user_input):
                yield chunk

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # --- Non-streaming ---
    result = resume_agent(thread_id, req.user_input)
    return ChatResponse(
        session_id=req.session_id,
        message=result["content"],
        interrupted=result["interrupted"],
        interrupt_prompt=result["interrupt_prompt"],
    )
