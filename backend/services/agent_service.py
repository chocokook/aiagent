"""
Agent service — wraps the LangGraph supervisor_hitl_agent for HTTP use.

Responsibilities:
- Lazy-load a single shared agent instance (expensive to create)
- Invoke / stream the agent for a given thread_id
- Detect HITL interrupts and surface them to the API layer
- Resume interrupted threads with user input
"""

import hashlib
import logging
import re
import time
from typing import AsyncGenerator, Optional

import redis as redis_lib
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langgraph.types import Interrupt

from config import Context, DEFAULT_MODEL
from backend.metrics import (
    cache_hits_total,
    cache_misses_total,
    conversations_total,
    escalation_total,
    ttft_seconds,
    verification_triggered_total,
    verification_skipped_total,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared agent instance (created once on first use)
# ---------------------------------------------------------------------------
_agent = None

# ---------------------------------------------------------------------------
# Redis response cache
# Caches final answers for non-personal general questions (e.g. "return policy").
# Cache key = MD5 of normalised message text. TTL = 1 hour.
# ---------------------------------------------------------------------------
_CACHE_TTL = 3600  # seconds
_redis: Optional[redis_lib.Redis] = None

# Matches personal pronouns — same logic as supervisor_hitl_agent._PERSONAL_RE
_PERSONAL_RE = re.compile(
    r"\b(my|mine|i|i've|i'd|i'm|i'll|our|myself|me)\b",
    re.IGNORECASE,
)

# Matches escalation intent (user wants a human agent)
_ESCALATION_RE = re.compile(
    r"转人工|找人工|要人工|真人|人工客服|找客服|speak to (a |an )?(human|agent|person|representative)"
    r"|talk to (a |an )?(human|agent|person|representative)"
    r"|human agent|live agent|real person",
    re.IGNORECASE,
)


def _is_cacheable(message: str) -> bool:
    """Return True if the message is a general (non-personal) query safe to cache."""
    return not bool(_PERSONAL_RE.search(message))


def _get_redis() -> Optional[redis_lib.Redis]:
    global _redis
    if _redis is None:
        import os
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            client = redis_lib.from_url(redis_url, decode_responses=True, socket_connect_timeout=1)
            client.ping()
            _redis = client
            logger.info("Redis cache connected")
        except Exception as exc:
            logger.warning("Redis unavailable, caching disabled: %s", exc)
            _redis = False  # type: ignore[assignment]  # sentinel: don't retry
    return _redis if _redis else None


def _cache_key(message: str) -> str:
    normalised = message.lower().strip()
    return f"agent_response:{hashlib.md5(normalised.encode()).hexdigest()}"


def _cache_get(message: str) -> Optional[str]:
    r = _get_redis()
    if r is None:
        return None
    try:
        return r.get(_cache_key(message))
    except Exception:
        return None


def _cache_set(message: str, response: str) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(_cache_key(message), _CACHE_TTL, response)
    except Exception:
        pass


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
    """Build LangGraph run config with thread_id and runtime context.

    LangGraph's context_schema=Context reads individual fields from configurable,
    so we pass 'model' directly rather than wrapping in a Context instance.
    """
    return {
        "configurable": {
            "thread_id": thread_id,
            "model": model,
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
    conversations_total.inc()

    # Escalation detection
    if _ESCALATION_RE.search(user_message):
        escalation_total.inc()

    # Cache hit: return immediately for repeated general questions
    if _is_cacheable(user_message):
        cached = _cache_get(user_message)
        if cached:
            logger.debug("Cache hit for: %.60s", user_message)
            cache_hits_total.inc()
            return {"content": cached, "interrupted": False, "interrupt_prompt": None}
        cache_misses_total.inc()
    else:
        verification_skipped_total.inc()

    agent = _get_agent()
    config = _build_config(thread_id, model)

    state_input = {"messages": [HumanMessage(content=user_message)]}
    result = agent.invoke(state_input, config=config)

    interrupt_prompt = _extract_interrupt(result)
    if interrupt_prompt:
        verification_triggered_total.inc()
        return {"content": "", "interrupted": True, "interrupt_prompt": interrupt_prompt}

    messages = result.get("messages", [])
    last_ai = next(
        (m.content for m in reversed(messages) if hasattr(m, "type") and m.type == "ai"),
        "",
    )

    # Store in cache for future identical queries
    if last_ai and _is_cacheable(user_message):
        _cache_set(user_message, last_ai)

    return {"content": last_ai, "interrupted": False, "interrupt_prompt": None}


async def stream_agent(
    thread_id: str,
    user_message: str,
    model: str = DEFAULT_MODEL,
) -> AsyncGenerator[str, None]:
    """
    Stream the agent response token by token via async generator.

    Uses asyncio.Queue to bridge the synchronous LangGraph stream and the
    async generator, so each token is yielded to the client immediately as
    the LLM generates it rather than buffered until completion.

    Yields SSE-formatted strings:
        "data: <token>\n\n"
        "data: [DONE]\n\n"
        "data: [INTERRUPT] <prompt>\n\n"   ← when HITL pause occurs
    """
    import asyncio
    import json

    conversations_total.inc()

    # Escalation detection
    if _ESCALATION_RE.search(user_message):
        escalation_total.inc()

    # Cache hit: yield cached response instantly (no LLM call needed)
    if _is_cacheable(user_message):
        cached = _cache_get(user_message)
        if cached:
            logger.debug("Stream cache hit for: %.60s", user_message)
            cache_hits_total.inc()
            yield f"data: {json.dumps(cached)}\n\n"
            yield "data: [DONE]\n\n"
            return
        cache_misses_total.inc()
    else:
        verification_skipped_total.inc()

    agent = _get_agent()
    config = _build_config(thread_id, model)
    state_input = {"messages": [HumanMessage(content=user_message)]}
    _request_start = time.monotonic()  # T1: user message received

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    # Internal nodes that produce structured JSON (not user-facing)
    _INTERNAL_NODES = {"query_router", "verify_customer", "collect_email"}
    _SENTINEL = object()

    def _run_stream():
        try:
            for chunk in agent.stream(state_input, config=config, stream_mode="messages"):
                if isinstance(chunk, tuple):
                    msg_chunk, metadata = chunk
                    node = metadata.get("langgraph_node", "")
                    if node in _INTERNAL_NODES:
                        continue
                    # Forward LLM-generated AI messages; skip ToolMessages, HumanMessages, etc.
                    # Note: LangGraph yields complete AIMessage (not AIMessageChunk) here because
                    # the inner agents run synchronously — true token streaming is unavailable.
                    if isinstance(msg_chunk, (AIMessage, AIMessageChunk)) and msg_chunk.content:
                        loop.call_soon_threadsafe(queue.put_nowait, ("token", msg_chunk.content))
                elif isinstance(chunk, dict) and "__interrupt__" in chunk:
                    interrupts = chunk["__interrupt__"]
                    if interrupts:
                        loop.call_soon_threadsafe(queue.put_nowait, ("interrupt", str(interrupts[0].value)))
        except Exception as exc:
            logger.error("stream_agent full traceback:", exc_info=True)
            loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, (_SENTINEL, None))

    loop.run_in_executor(None, _run_stream)

    collected_tokens: list[str] = []
    interrupted = False
    _first_token_recorded = False

    while True:
        kind, value = await queue.get()
        if kind is _SENTINEL:
            yield "data: [DONE]\n\n"
            break
        elif kind == "interrupt":
            interrupted = True
            verification_triggered_total.inc()
            yield f"data: [INTERRUPT] {value}\n\n"
            break
        elif kind == "error":
            logger.error("stream_agent error: %s", value)
            yield "data: [DONE]\n\n"
            break
        else:
            import json
            # Record TTFT on first token
            if not _first_token_recorded:
                ttft_seconds.observe(time.monotonic() - _request_start)
                _first_token_recorded = True
            collected_tokens.append(value)
            yield f"data: {json.dumps(value)}\n\n"

    # Store assembled response in cache for future identical queries
    if not interrupted and collected_tokens and _is_cacheable(user_message):
        _cache_set(user_message, "".join(collected_tokens))


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
    """Streaming version of resume_agent. Uses queue-based real streaming."""
    import asyncio
    from langgraph.types import Command

    agent = _get_agent()
    config = _build_config(thread_id, model)

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    _INTERNAL_NODES = {"query_router", "verify_customer", "collect_email"}
    _SENTINEL = object()

    def _run_stream():
        try:
            for chunk in agent.stream(Command(resume=user_input), config=config, stream_mode="messages"):
                if isinstance(chunk, tuple):
                    msg_chunk, metadata = chunk
                    node = metadata.get("langgraph_node", "")
                    if node in _INTERNAL_NODES:
                        continue
                    # Forward LLM-generated AI messages; skip ToolMessages, HumanMessages, etc.
                    # Note: LangGraph yields complete AIMessage (not AIMessageChunk) here because
                    # the inner agents run synchronously — true token streaming is unavailable.
                    if isinstance(msg_chunk, (AIMessage, AIMessageChunk)) and msg_chunk.content:
                        loop.call_soon_threadsafe(queue.put_nowait, ("token", msg_chunk.content))
                elif isinstance(chunk, dict) and "__interrupt__" in chunk:
                    interrupts = chunk["__interrupt__"]
                    if interrupts:
                        loop.call_soon_threadsafe(queue.put_nowait, ("interrupt", str(interrupts[0].value)))
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, (_SENTINEL, None))

    loop.run_in_executor(None, _run_stream)

    while True:
        kind, value = await queue.get()
        if kind is _SENTINEL:
            yield "data: [DONE]\n\n"
            break
        elif kind == "interrupt":
            yield f"data: [INTERRUPT] {value}\n\n"
            break
        elif kind == "error":
            logger.error("stream_resume_agent error: %s", value)
            yield "data: [DONE]\n\n"
            break
        else:
            import json
            yield f"data: {json.dumps(value)}\n\n"
