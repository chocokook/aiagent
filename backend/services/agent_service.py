"""
Agent service — wraps the LangGraph supervisor_hitl_agent for HTTP use.

Responsibilities:
- Lazy-load a single shared agent instance (expensive to create)
- Invoke / stream the agent for a given thread_id
- Detect HITL interrupts and surface them to the API layer
- Resume interrupted threads with user input
"""

import logging
from typing import AsyncGenerator, Optional

from langchain_core.messages import HumanMessage
from langgraph.types import Interrupt

from config import Context, DEFAULT_MODEL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared agent instance (created once on first use)
# ---------------------------------------------------------------------------
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        from agents import create_supervisor_hitl_agent

        # use_checkpointer=True so MemorySaver keeps conversation history per thread_id
        _agent = create_supervisor_hitl_agent(use_checkpointer=True)
        logger.info("LangGraph agent loaded")
    return _agent


# ---------------------------------------------------------------------------
# Invoke helpers
# ---------------------------------------------------------------------------


def _build_config(thread_id: str, model: str = DEFAULT_MODEL) -> dict:
    """Build LangGraph run config with thread_id and runtime context."""
    return {
        "configurable": {
            "thread_id": thread_id,
            "context": Context(model=model),
        }
    }


def _extract_interrupt(result) -> Optional[str]:
    """Return the interrupt prompt if the graph paused, else None."""
    # LangGraph surfaces interrupts as Interrupt objects inside __interrupt__
    interrupts = result.get("__interrupt__", [])
    if interrupts:
        first: Interrupt = interrupts[0]
        return str(first.value)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def invoke_agent(
    thread_id: str,
    user_message: str,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Invoke the agent synchronously.

    Returns:
        {
            "content": str,        # agent's reply
            "interrupted": bool,   # True if HITL pause
            "interrupt_prompt": str | None,
        }
    """
    agent = _get_agent()
    config = _build_config(thread_id, model)

    state_input = {"messages": [HumanMessage(content=user_message)]}
    result = agent.invoke(state_input, config=config)

    interrupt_prompt = _extract_interrupt(result)
    if interrupt_prompt:
        return {"content": "", "interrupted": True, "interrupt_prompt": interrupt_prompt}

    messages = result.get("messages", [])
    last_ai = next(
        (m.content for m in reversed(messages) if hasattr(m, "type") and m.type == "ai"),
        "",
    )
    return {"content": last_ai, "interrupted": False, "interrupt_prompt": None}


async def stream_agent(
    thread_id: str,
    user_message: str,
    model: str = DEFAULT_MODEL,
) -> AsyncGenerator[str, None]:
    """
    Stream the agent response token by token via async generator.

    Yields SSE-formatted strings:
        "data: <token>\n\n"
        "data: [DONE]\n\n"
        "data: [INTERRUPT] <prompt>\n\n"   ← when HITL pause occurs
    """
    import asyncio

    agent = _get_agent()
    config = _build_config(thread_id, model)
    state_input = {"messages": [HumanMessage(content=user_message)]}

    loop = asyncio.get_event_loop()

    def _run_stream():
        chunks = []
        interrupted = False
        interrupt_prompt = None
        for chunk in agent.stream(state_input, config=config, stream_mode="messages"):
            # chunk is (message_chunk, metadata) in messages stream mode
            if isinstance(chunk, tuple):
                msg_chunk, _ = chunk
                if hasattr(msg_chunk, "content") and msg_chunk.content:
                    chunks.append(msg_chunk.content)
            elif isinstance(chunk, dict) and "__interrupt__" in chunk:
                interrupts = chunk["__interrupt__"]
                if interrupts:
                    interrupted = True
                    interrupt_prompt = str(interrupts[0].value)
        return chunks, interrupted, interrupt_prompt

    chunks, interrupted, interrupt_prompt = await loop.run_in_executor(None, _run_stream)

    if interrupted:
        yield f"data: [INTERRUPT] {interrupt_prompt}\n\n"
    else:
        for token in chunks:
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"


def resume_agent(
    thread_id: str,
    user_input: str,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Resume a HITL-interrupted agent thread with the user's response.

    Returns same shape as invoke_agent().
    """
    agent = _get_agent()
    config = _build_config(thread_id, model)

    # LangGraph resumes an interrupted graph by passing None as input
    # and providing the user's answer via the Command primitive
    from langgraph.types import Command

    result = agent.invoke(Command(resume=user_input), config=config)

    interrupt_prompt = _extract_interrupt(result)
    if interrupt_prompt:
        return {"content": "", "interrupted": True, "interrupt_prompt": interrupt_prompt}

    messages = result.get("messages", [])
    last_ai = next(
        (m.content for m in reversed(messages) if hasattr(m, "type") and m.type == "ai"),
        "",
    )
    return {"content": last_ai, "interrupted": False, "interrupt_prompt": None}


async def stream_resume_agent(
    thread_id: str,
    user_input: str,
    model: str = DEFAULT_MODEL,
) -> AsyncGenerator[str, None]:
    """Streaming version of resume_agent."""
    import asyncio
    from langgraph.types import Command

    agent = _get_agent()
    config = _build_config(thread_id, model)

    loop = asyncio.get_event_loop()

    def _run_stream():
        chunks = []
        interrupted = False
        interrupt_prompt = None
        for chunk in agent.stream(Command(resume=user_input), config=config, stream_mode="messages"):
            if isinstance(chunk, tuple):
                msg_chunk, _ = chunk
                if hasattr(msg_chunk, "content") and msg_chunk.content:
                    chunks.append(msg_chunk.content)
            elif isinstance(chunk, dict) and "__interrupt__" in chunk:
                interrupts = chunk["__interrupt__"]
                if interrupts:
                    interrupted = True
                    interrupt_prompt = str(interrupts[0].value)
        return chunks, interrupted, interrupt_prompt

    chunks, interrupted, interrupt_prompt = await loop.run_in_executor(None, _run_stream)

    if interrupted:
        yield f"data: [INTERRUPT] {interrupt_prompt}\n\n"
    else:
        for token in chunks:
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"
