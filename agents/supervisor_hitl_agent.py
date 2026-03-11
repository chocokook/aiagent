# agents/supervisor_hitl_agent.py
"""
Customer Verification + Supervisor Agent with HITL

This module creates a complete customer support agent that combines:
- Query classification (does this need identity verification?)
- Human-in-the-loop (HITL) email collection and validation
- Supervisor agent routing to specialized sub-agents

Architecture: the supervisor LLM is inlined directly into this graph (rather than
wrapped as a compiled subgraph) so that its tokens stream in real time to the caller.

Graph structure:
    START
      └─► query_router
            ├─► verify_customer ─► collect_email ─► verify_customer (loop)
            │         └─► supervisor_llm
            └─► supervisor_llm ◄──────────────────────────────────────────┐
                      │                                                    │
                      ├─► supervisor_tools (calls db/docs agents) ────────┘
                      └─► END
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal, NamedTuple

from langchain.chat_models import init_chat_model
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool as lc_tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command, interrupt
from langgraph.runtime import Runtime
from typing_extensions import Annotated, TypedDict

from agents.db_agent import create_db_agent
from agents.docs_agent import create_docs_agent
from config import DEFAULT_MODEL, Context
from tools import get_customer_orders
from tools.database import get_database

# ============================================================================
# SUPERVISOR SYSTEM PROMPT
# (Inlined here now that the supervisor LLM lives in this graph)
# ============================================================================

_SUPERVISOR_SYSTEM_PROMPT = """You are a supervisor agent for TechHub customer support.

Your role is to interact with customers to understand their questions, use the sub-agent tools provided to
gather information needed to answer their questions, and then provide helpful responses to the customer.

Capabilities:
- Interact with customers to understand their questions
- Formulate queries to the database_specialist to help answer questions about orders (status, details), products (prices, availability), and customer accounts.
- Formulate queries to the documentation_specialist to help answer questions about product specs, policies, warranties, and setup instructions

IMPORTANT:
- For the database_specialist, if the question requires finding information about a specific customer, you will need to include the customer's email AND customer_id in your query!
- Do not answer questions about the database or documentation by yourself, always use the tools provided to you to get the information you need.
- Be sure to phrase your queries to the sub-agents from your perspective as the supervisor agent, not the customer's perspective.
- If the customer asks to cancel an order, check that the order is eligible for cancellation, and then let the customer know you will cancel the order.

You can use multiple tools if needed to fully answer the question.
Always provide helpful, accurate, concise, and specific responses to customer questions.

RESPONSE STYLE:
- Write in a friendly, professional customer service tone — you are talking directly to a customer.
- Synthesize the specialist's information into a clear, natural response. Do NOT dump raw document content verbatim.
- Use plain language. When the specialist returns structured data (bullet lists, sections), reformat it in a way that reads naturally for the customer.
- Be concise: highlight the key points relevant to the customer's question, don't copy every detail from the document.
- Do NOT start your reply with phrases like "Here is the information:", "According to our documentation:", or "Based on what our specialist found:". Just answer naturally.
- If the information has important structure (e.g. different rules for different product types), you may use a short list — but write a brief lead-in sentence first."""

# ============================================================================
# CUSTOM STATE SCHEMA
# ============================================================================


class IntermediateState(MessagesState):
    """Intermediate MessagesState with customer_id for verification tracking."""
    customer_id: str


# ============================================================================
# HELPER SCHEMAS AND FUNCTIONS
# ============================================================================


class QueryClassification(TypedDict):
    """Classification of whether customer identity verification is required."""

    reasoning: Annotated[
        str, ..., "Brief explanation of why verification is or isn't needed"
    ]
    requires_verification: Annotated[
        bool,
        ...,
        "True if the query requires knowing customer identity (e.g., 'my orders', 'my account', 'my purchases'). False for general questions (product info, policies, how-to questions).",
    ]


class EmailExtraction(TypedDict):
    """Schema for extracting email from user message."""

    email: Annotated[
        str,
        ...,
        "The email address extracted from the message, or empty string if none found",
    ]


class CustomerInfo(NamedTuple):
    """Customer information returned from validation."""

    customer_id: str
    customer_name: str


# Matches personal pronouns that indicate the query is about a specific customer.
# If none match, verification is definitely not needed — skip the LLM call.
_PERSONAL_RE = re.compile(
    r"\b(my|mine|i|i've|i'd|i'm|i'll|our|myself|me)\b",
    re.IGNORECASE,
)


def _fast_needs_verification(query: str) -> bool | None:
    """Keyword fast-path before calling LLM classifier.

    Returns:
        False  — definitely no personal reference, skip verification
        None   — uncertain, fall back to LLM
    """
    if _PERSONAL_RE.search(query):
        return None  # might need verification; let LLM decide
    return False  # no personal pronoun → general question → no verification needed


def classify_query_intent(query: str, model: str = DEFAULT_MODEL) -> QueryClassification:
    """Classify whether a query requires customer identity verification."""
    llm = init_chat_model(model, configurable_fields=["model"])
    structured_llm = llm.with_structured_output(QueryClassification)
    classification_prompt = """Analyze the following user's query to determine if it requires knowing their customer identity in order to answer the question."""

    return structured_llm.invoke(
        [
            {"role": "system", "content": classification_prompt},
            {"role": "user", "content": query},
        ]
    )


def create_email_extractor(model: str = DEFAULT_MODEL):
    """Create an LLM configured to extract emails from natural language."""
    llm = init_chat_model(model, configurable_fields=["model"])
    return llm.with_structured_output(EmailExtraction)


def validate_customer_email(email: str, db: SQLDatabase) -> CustomerInfo | None:
    """Validate email format and lookup customer in database."""
    if not email or "@" not in email:
        return None

    result = db._execute(
        f"SELECT customer_id, name FROM customers WHERE email = '{email}'"
    )
    result = [tuple(row.values()) for row in result]

    if not result:
        return None

    customer_id, customer_name = result[0]
    return CustomerInfo(customer_id=customer_id, customer_name=customer_name)


# ============================================================================
# VERIFICATION GRAPH NODES
# ============================================================================


def query_router(
    state: IntermediateState,
    runtime: Runtime[Context],
) -> Command[Literal["verify_customer", "supervisor_llm"]]:
    """Route query based on verification needs."""
    # Already verified? Skip to supervisor
    if state.get("customer_id"):
        return Command(goto="supervisor_llm")

    last_message = state["messages"][-1]

    # Fast keyword check: no personal pronouns → skip LLM call entirely
    if _fast_needs_verification(last_message.content) is False:
        return Command(goto="supervisor_llm")

    model = runtime.context.model if runtime.context else DEFAULT_MODEL
    query_classification = classify_query_intent(last_message.content, model=model)

    if query_classification.get("requires_verification"):
        return Command(goto="verify_customer")
    return Command(goto="supervisor_llm")


def verify_customer(
    state: IntermediateState,
    runtime: Runtime[Context],
) -> Command[Literal["supervisor_llm", "collect_email"]]:
    """Ensure we have a valid customer email and set the customer_id in state."""
    last_message = state["messages"][-1]

    model = runtime.context.model if runtime.context else DEFAULT_MODEL
    email_extractor = create_email_extractor(model=model)
    extraction = email_extractor.invoke([last_message])

    if extraction["email"]:
        db = get_database()
        customer = validate_customer_email(extraction["email"], db)

        if customer:
            return Command(
                update={
                    "customer_id": customer.customer_id,
                    "messages": [
                        AIMessage(content=f"✓ Verified! Welcome back, {customer.customer_name}.")
                    ],
                },
                goto="supervisor_llm",
            )
        else:
            return Command(
                update={
                    "messages": [
                        AIMessage(
                            content=f"I couldn't find '{extraction['email']}' in our system. Please check and try again."
                        )
                    ]
                },
                goto="collect_email",
            )

    return Command(
        update={
            "messages": [
                AIMessage(
                    content="To access information about your account or orders, please provide your email address."
                )
            ]
        },
        goto="collect_email",
    )


def collect_email(state: IntermediateState) -> Command[Literal["verify_customer"]]:
    """Dedicated node for collecting human input via interrupt."""
    user_input = interrupt(value="Please provide your email:")
    return Command(
        update={"messages": [HumanMessage(content=user_input)]}, goto="verify_customer"
    )


# ============================================================================
# FACTORY FUNCTION
# ============================================================================


def create_supervisor_hitl_agent(
    db_agent=None,
    docs_agent=None,
    use_checkpointer: bool = True,
):
    """Create customer verification + supervisor agent with HITL.

    The supervisor LLM is inlined as a direct node in this graph (not a subgraph),
    enabling true token-level streaming to the caller.

    Args:
        db_agent: Optional pre-configured database agent.
        docs_agent: Optional pre-configured documents agent.
        use_checkpointer: True for development (MemorySaver), False for LangGraph Cloud.

    Returns:
        Compiled graph with HITL verification and streaming supervisor.
    """
    if db_agent is None:
        db_agent = create_db_agent(
            additional_tools=[get_customer_orders],
            use_checkpointer=use_checkpointer,
        )

    if docs_agent is None:
        docs_agent = create_docs_agent(use_checkpointer=use_checkpointer)

    # ------------------------------------------------------------------
    # Define specialist tool functions (close over the compiled agents)
    # ------------------------------------------------------------------

    @lc_tool(
        "database_specialist",
        description="Query TechHub database specialist for order status, order details, product prices, product availability, and customer accounts.",
    )
    def call_database_specialist(query: str) -> str:
        result = db_agent.invoke({"messages": [{"role": "user", "content": query}]})
        return result["messages"][-1].content

    @lc_tool(
        "documentation_specialist",
        description="Query TechHub documentation specialist to search for product specs, policies, warranties, and setup instructions.",
    )
    def call_documentation_specialist(query: str) -> str:
        result = docs_agent.invoke({"messages": [{"role": "user", "content": query}]})
        return result["messages"][-1].content

    _specialist_tools = [call_database_specialist, call_documentation_specialist]
    _tool_map = {t.name: t for t in _specialist_tools}

    # Cache bound LLM instances by model name to avoid recreating on every call.
    _llm_cache: dict = {}

    # ------------------------------------------------------------------
    # Supervisor LLM node
    # Inlined here so LangGraph can stream its tokens directly.
    # ------------------------------------------------------------------

    def supervisor_llm(
        state: IntermediateState,
        runtime: Runtime[Context],
    ) -> dict:
        """Call the supervisor LLM. Streams tokens directly in the parent graph."""
        model = runtime.context.model if runtime.context else DEFAULT_MODEL

        # Reuse bound LLM instance for the same model (avoids recreating every call)
        if model not in _llm_cache:
            _llm_cache[model] = init_chat_model(model).bind_tools(_specialist_tools)
        llm = _llm_cache[model]

        # Inject customer_id into system prompt if verified
        system_content = _SUPERVISOR_SYSTEM_PROMPT
        customer_id = state.get("customer_id")
        if customer_id:
            system_content += f"\n\nThe customer's ID in this conversation is: {customer_id}"

        messages = [SystemMessage(content=system_content)] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    # ------------------------------------------------------------------
    # Supervisor tools node
    # Runs multiple tool calls in parallel (ThreadPoolExecutor).
    # Single tool call skips the overhead and runs directly.
    # ------------------------------------------------------------------

    def supervisor_tools(state: IntermediateState) -> dict:
        """Execute tool calls in parallel when multiple tools are requested."""
        last = state["messages"][-1]
        tool_calls = last.tool_calls

        if len(tool_calls) == 1:
            # Single tool — no threading overhead needed
            tc = tool_calls[0]
            result = _tool_map[tc["name"]].invoke(tc["args"])
            return {"messages": [ToolMessage(content=result, tool_call_id=tc["id"])]}

        # Multiple tools — run in parallel, preserve original order
        results_map: dict = {}
        with ThreadPoolExecutor(max_workers=len(tool_calls)) as executor:
            futures = {
                executor.submit(_tool_map[tc["name"]].invoke, tc["args"]): tc
                for tc in tool_calls
            }
            for future in as_completed(futures):
                tc = futures[future]
                results_map[tc["id"]] = future.result()

        return {
            "messages": [
                ToolMessage(content=results_map[tc["id"]], tool_call_id=tc["id"])
                for tc in tool_calls  # preserve original order
            ]
        }

    # ------------------------------------------------------------------
    # Routing: continue tool loop or finish
    # ------------------------------------------------------------------

    def route_supervisor(state: IntermediateState) -> Literal["supervisor_tools", "__end__"]:
        """After supervisor LLM: call tools if requested, else end."""
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "supervisor_tools"
        return END

    # ------------------------------------------------------------------
    # Build the graph
    # ------------------------------------------------------------------

    workflow = StateGraph(
        input_schema=MessagesState,
        state_schema=IntermediateState,
        output_schema=MessagesState,
        context_schema=Context,
    )

    workflow.add_node("query_router", query_router)
    workflow.add_node("verify_customer", verify_customer)
    workflow.add_node("collect_email", collect_email)
    workflow.add_node("supervisor_llm", supervisor_llm)
    workflow.add_node("supervisor_tools", supervisor_tools)

    workflow.add_edge(START, "query_router")
    workflow.add_conditional_edges(
        "supervisor_llm",
        route_supervisor,
        {"supervisor_tools": "supervisor_tools", END: END},
    )
    workflow.add_edge("supervisor_tools", "supervisor_llm")

    if use_checkpointer:
        return workflow.compile(checkpointer=MemorySaver(), name="supervisor_hitl_agent")
    else:
        return workflow.compile(name="supervisor_hitl_agent")
