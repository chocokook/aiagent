"""
Pydantic schemas for the TechHub customer support API.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat message."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Request body for POST /chat."""

    message: str = Field(..., description="User's message")
    session_id: Optional[str] = Field(
        None, description="Session ID for conversation continuity. Auto-created if omitted."
    )
    stream: bool = Field(True, description="Whether to stream the response via SSE")


class ChatResponse(BaseModel):
    """Non-streaming response body for POST /chat."""

    session_id: str
    message: str
    interrupted: bool = Field(
        False,
        description="True when the agent is paused waiting for user input (e.g. email verification)",
    )
    interrupt_prompt: Optional[str] = Field(
        None, description="Question shown to the user when interrupted"
    )


class ResumeRequest(BaseModel):
    """Request body for POST /chat/resume — continues an interrupted HITL flow."""

    session_id: str = Field(..., description="Session ID of the interrupted conversation")
    user_input: str = Field(..., description="User's response to the interrupt prompt")
    stream: bool = Field(True, description="Whether to stream the response via SSE")


class SessionInfo(BaseModel):
    """Session metadata returned by GET /sessions/{session_id}."""

    session_id: str
    created_at: str
    message_count: int
    customer_id: Optional[str] = None
