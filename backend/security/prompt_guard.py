"""
Prompt injection detection and forbidden word filtering.

Usage:
    from backend.security import PromptGuard
    guard = PromptGuard()
    guard.validate(user_input)   # raises HTTPException on violation
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException

from backend.metrics import prompt_injection_blocks, forbidden_word_blocks

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Injection attack patterns (case-insensitive)
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS = [
    # Instruction override
    r"ignore\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|rules?|directives?)",
    r"forget\s+(all\s+)?(your\s+)?(instructions?|prompts?|rules?|training)",
    r"disregard\s+(all\s+)?(previous|prior|your)\s+(instructions?|prompts?|rules?)",
    r"override\s+(your\s+)?(instructions?|system\s+prompt|directives?)",
    # Role hijacking
    r"you\s+are\s+now\s+(a\s+|an\s+)?(?!customer|support|assistant\b)\w+",
    r"act\s+as\s+(a\s+|an\s+)?(different|new|another|unrestricted|evil|jailbroken)",
    r"pretend\s+(you\s+are|to\s+be)\s+(a\s+|an\s+)?(different|new|another|unrestricted)",
    r"roleplay\s+as\s+(a\s+|an\s+)?(different|new|another|unrestricted)",
    # System prompt exfiltration
    r"(show|print|reveal|repeat|tell me|what is|display)\s+(your|the)\s+system\s+prompt",
    r"(show|print|reveal|repeat|tell me)\s+(your|the)\s+(initial|original|hidden|secret)\s+(instructions?|prompts?)",
    r"what\s+(were\s+you|are\s+you)\s+told\s+to",
    # Jailbreak keywords
    r"\bDAN\b",  # Do Anything Now
    r"jailbreak",
    r"do\s+anything\s+now",
    r"no\s+restrictions?\b",
    r"without\s+(any\s+)?(restrictions?|limits?|filters?|guidelines?)",
    # Developer/debug mode tricks
    r"(enable|activate|switch\s+to)\s+(developer|debug|god|admin|unrestricted)\s+mode",
    r"(you\s+are\s+in|enter)\s+(developer|debug|training)\s+mode",
    # Prompt delimiter injection
    r"</?(system|human|assistant|instruction)>",
    r"\[INST\]|\[/INST\]",
    r"###\s*(Instruction|System|Human|Assistant)",
]

# ---------------------------------------------------------------------------
# Forbidden words for customer support context
# ---------------------------------------------------------------------------
_FORBIDDEN_WORDS = [
    # Competitor attacks (TechHub context)
    r"\b(amazon|alibaba|jd\.com|newegg)\s+(is\s+)?(better|cheaper|superior|worse|terrible)",
    # Spam / solicitation
    r"click\s+here\s+to\s+(win|claim|get)",
    r"congratulations\s+you\s+(have\s+)?(won|been\s+selected)",
    # Profanity (basic set — extend as needed)
    r"\bf[*u]ck\b",
    r"\bsh[*i]t\b",
    r"\ba[*s]s(hole)?\b",
    # Personal data harvesting
    r"(give\s+me|send\s+me|share)\s+(all\s+)?(customer|user)\s+(data|records|emails|passwords)",
    r"(dump|export|extract)\s+(the\s+)?(database|db|all\s+users)",
]

_INJECTION_RE = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _INJECTION_PATTERNS]
_FORBIDDEN_RE = [re.compile(p, re.IGNORECASE) for p in _FORBIDDEN_WORDS]


@dataclass
class GuardResult:
    blocked: bool
    reason: Optional[str] = None
    matched_pattern: Optional[str] = None


class PromptGuard:
    """Validates user input before forwarding to the LLM agent."""

    # Maximum input length (characters)
    MAX_LENGTH = 2000

    def check_length(self, text: str) -> GuardResult:
        if len(text) > self.MAX_LENGTH:
            return GuardResult(
                blocked=True,
                reason=f"Message too long ({len(text)} chars, max {self.MAX_LENGTH})",
            )
        return GuardResult(blocked=False)

    def check_injection(self, text: str) -> GuardResult:
        for pattern in _INJECTION_RE:
            match = pattern.search(text)
            if match:
                logger.warning(
                    "Prompt injection blocked | pattern=%s | snippet=%r",
                    pattern.pattern[:60],
                    text[:100],
                )
                prompt_injection_blocks.inc()
                return GuardResult(
                    blocked=True,
                    reason="Your message contains content that cannot be processed.",
                    matched_pattern=pattern.pattern[:60],
                )
        return GuardResult(blocked=False)

    def check_forbidden(self, text: str) -> GuardResult:
        for pattern in _FORBIDDEN_RE:
            match = pattern.search(text)
            if match:
                logger.warning(
                    "Forbidden content blocked | pattern=%s | snippet=%r",
                    pattern.pattern[:60],
                    text[:100],
                )
                forbidden_word_blocks.inc()
                return GuardResult(
                    blocked=True,
                    reason="Your message contains content that is not allowed.",
                    matched_pattern=pattern.pattern[:60],
                )
        return GuardResult(blocked=False)

    def validate(self, text: str) -> None:
        """
        Run all checks. Raises HTTPException(400) if any check fails.
        Safe messages pass through silently.
        """
        for check in (self.check_length, self.check_injection, self.check_forbidden):
            result = check(text)
            if result.blocked:
                raise HTTPException(status_code=400, detail=result.reason)


# Module-level singleton
_guard = PromptGuard()


def validate_input(text: str) -> None:
    """Convenience function for use in route handlers."""
    _guard.validate(text)
