"""
Semantic response cache backed by Redis.

Instead of exact-string matching, embeds each question and finds the most
similar cached entry using cosine similarity. Cache hits save an LLM call
at the cost of one embedding API call per request.

Storage layout:
  qa:faq:{uuid}   →  JSON { question, response, embedding: [float, ...] }
  qa:faq:index    →  Redis list of all active qa:faq:* keys
"""

import json
import logging
import math
import os
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

_FAQ_TTL = 7 * 24 * 3600   # 7 days for general FAQ questions
_SIMILARITY_THRESHOLD = 0.92
_INDEX_KEY = "qa:faq:index"


def _get_embedding(text: str) -> list[float]:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text.lower().strip(),
    )
    return response.data[0].embedding


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_cache_get(r, question: str) -> Optional[str]:
    """
    Return a cached response if a semantically similar question was seen before,
    otherwise return None.
    """
    try:
        index = r.lrange(_INDEX_KEY, 0, -1)
        if not index:
            return None

        query_embedding = _get_embedding(question)

        best_score = 0.0
        best_response: Optional[str] = None

        for key in index:
            raw = r.get(key)
            if not raw:
                continue
            entry = json.loads(raw)
            score = _cosine_similarity(query_embedding, entry["embedding"])
            if score > best_score:
                best_score = score
                best_response = entry["response"]

        if best_score >= _SIMILARITY_THRESHOLD and best_response is not None:
            logger.debug("Semantic cache hit (similarity=%.3f)", best_score)
            return best_response

        logger.debug("Semantic cache miss (best similarity=%.3f)", best_score)
        return None

    except Exception as exc:
        logger.warning("Semantic cache lookup failed: %s", exc)
        return None


def semantic_cache_set(r, question: str, response: str) -> None:
    """
    Store a question/response pair with its embedding for future semantic lookup.
    """
    try:
        embedding = _get_embedding(question)
        key = f"qa:faq:{uuid.uuid4().hex}"
        entry = {
            "question": question,
            "response": response,
            "embedding": embedding,
        }
        r.setex(key, _FAQ_TTL, json.dumps(entry))
        r.rpush(_INDEX_KEY, key)
        r.expire(_INDEX_KEY, _FAQ_TTL)
        logger.debug("Semantic cache stored: %.60s", question)
    except Exception as exc:
        logger.warning("Semantic cache store failed: %s", exc)
