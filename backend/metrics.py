"""
Centralised Prometheus metric definitions for TechHub.

Import from here in any module that needs to increment a counter.
"""

from prometheus_client import Counter, Histogram

# Security
prompt_injection_blocks = Counter(
    "techhub_prompt_injection_blocks_total",
    "Requests blocked by prompt injection guard",
)
forbidden_word_blocks = Counter(
    "techhub_forbidden_word_blocks_total",
    "Requests blocked by forbidden word filter",
)

# Conversations & Sessions
conversations_total = Counter(
    "techhub_conversations_total",
    "Total chat messages received",
)
sessions_started_total = Counter(
    "techhub_sessions_started_total",
    "Total new sessions created (denominator for escalation rate, first-contact rate)",
)

# Cache
cache_hits_total = Counter(
    "techhub_cache_hits_total",
    "Responses served from Redis cache (no LLM call needed)",
)
cache_misses_total = Counter(
    "techhub_cache_misses_total",
    "General queries that were not in cache and required LLM call",
)

# Identity verification
verification_triggered_total = Counter(
    "techhub_verification_triggered_total",
    "Conversations where HITL identity verification was triggered",
)
verification_skipped_total = Counter(
    "techhub_verification_skipped_total",
    "Queries routed directly without identity verification (no personal pronouns)",
)

# Escalation to human agent
escalation_total = Counter(
    "techhub_escalation_total",
    "Sessions where user requested human agent (转人工)",
)

# Response time — time to first token (TTFT)
ttft_seconds = Histogram(
    "techhub_ttft_seconds",
    "Time from user message to first AI token returned (seconds)",
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, float("inf")],
)

# Order query reliability
order_query_total = Counter(
    "techhub_order_query_total",
    "Total order-related tool calls (get_order_status, get_customer_orders, etc.)",
)
order_query_failed_total = Counter(
    "techhub_order_query_failed_total",
    "Order tool calls that returned no data or raised an exception",
)

# User feedback
feedback_resolved_total = Counter(
    "techhub_feedback_resolved_total",
    "Feedback submissions where user marked issue as resolved",
)
feedback_unresolved_total = Counter(
    "techhub_feedback_unresolved_total",
    "Feedback submissions where user marked issue as unresolved",
)
satisfaction_score_sum = Counter(
    "techhub_satisfaction_score_sum",
    "Sum of all satisfaction scores (divide by count for average)",
)
satisfaction_score_count = Counter(
    "techhub_satisfaction_score_count",
    "Number of satisfaction ratings submitted",
)

# First-contact resolution (1 user message + resolved)
first_contact_resolved_total = Counter(
    "techhub_first_contact_resolved_total",
    "Sessions resolved in a single user message (first-contact resolution)",
)
