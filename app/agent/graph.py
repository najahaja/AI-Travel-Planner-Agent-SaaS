"""
LangGraph Travel Planner Agent
==============================
Multi-step stateful agent that:
1. Classifies user intent
2. Routes to specialized tool nodes (RAG, weather, budget, itinerary)
3. Synthesizes a final, structured response
4. Persists the trip plan if applicable

FIXES APPLIED:
- [FIX 1] Human message now appended to messages in synthesize_response (was missing)
- [FIX 2] Stale tool data cleared at start of each turn in classify_intent
- [FIX 3] System prompt context injection is now gated by intent (general Q won't get trip format)
- [FIX 4] gather_data_node exits early for general_question / greeting / unclear
- [FIX 5] History window size standardized to 8 messages across all nodes
- [FIX 6] travelers fallback uses `or 1` instead of inline default to handle 0/None correctly
"""

from typing import TypedDict, Annotated, List, Optional, Any, Dict
from datetime import datetime
import operator
import json
import asyncio

# pyrefly: ignore [missing-import]
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.agent.llm import get_llm
from app.agent.tools.weather import get_weather_info
from app.agent.tools.budget import estimate_budget
from app.agent.tools.itinerary import build_itinerary

from app.agent.tools.places import search_places_to_visit, format_places_for_prompt
from app.rag.retriever import retrieve_travel_info
# pyrefly: ignore [missing-import]
from loguru import logger


# ── Constants ─────────────────────────────────────────────────────────────────

# Intents that should NOT trigger any tool calls
PASSIVE_INTENTS = {"greeting", "general_question", "unclear"}

# Intents that need weather data
WEATHER_INTENTS  = {"weather_info", "itinerary_planning", "budget_estimation"}

# Intents that need places data
PLACES_INTENTS   = {"destination_research", "itinerary_planning"}

# Intents that need budget data
BUDGET_INTENTS   = {"budget_estimation", "itinerary_planning"}

# How many past messages to include for context (consistent across all nodes)
HISTORY_WINDOW = 8


# ── Retry helper for Groq rate limiting ──────────────────────────────────────

async def invoke_with_retry(llm, messages, max_retries: int = 3, delay: float = 5.0):
    """Invoke the LLM with automatic retries on rate limit errors."""
    for attempt in range(max_retries):
        try:
            return await llm.ainvoke(messages)
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = (
                "rate_limit" in error_str
                or "429" in error_str
                or "too many" in error_str
            )
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = delay * (attempt + 1)   # 5 s → 10 s → 15 s
                logger.warning(
                    f"[LLM] Groq rate limit hit. "
                    f"Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})..."
                )
                await asyncio.sleep(wait_time)
            else:
                raise


# ── Agent State ───────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages:       Annotated[List[BaseMessage], operator.add]
    user_query:     str
    intent:         Optional[str]           # classified intent
    destination:    Optional[str]
    start_date:     Optional[str]
    end_date:       Optional[str]
    travelers:      Optional[int]
    budget_range:   Optional[str]           # "budget" | "mid-range" | "luxury"
    rag_context:    Optional[str]
    weather_data:   Optional[Dict]
    places_data:    Optional[Dict]
    budget_data:    Optional[Dict]
    itinerary_data: Optional[Dict]
    final_response: Optional[str]
    travel_plan:    Optional[Dict]          # structured plan to save to DB
    error:          Optional[str]


# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert AI Travel Planner with deep knowledge of global destinations, 
travel logistics, budgeting, cultural insights, and itinerary design.

Your capabilities:
- Create detailed day-by-day itineraries
- Estimate realistic budgets (flights, hotels, food, activities)
- Provide weather insights and best travel times
- Offer visa requirements and travel advisories
- Recommend hidden gems and off-the-beaten-path experiences
- Search live Google Places data for attractions and places to visit
- Answer questions using a knowledge base of travel guides

Always respond in a professional, helpful, and enthusiastic manner.
When planning a trip, always ask for: destination, travel dates, number of travelers, and budget preference if not provided.
Structure your responses clearly with headers and bullet points.
Return response in clean Markdown format.
Do NOT escape new lines (no \\n in output).
Use proper Markdown syntax:
- Headings using #
- Bold using **
- Lists using numbers or -
Ensure output is formatted for direct rendering in UI, not as a JSON string."""


# ── Helper: build recent-history string ──────────────────────────────────────

def _build_history_string(state: AgentState) -> str:
    """Return a compact string of the last HISTORY_WINDOW messages."""
    past_messages = state.get("messages", [])
    if not past_messages:
        return ""
    lines = []
    for m in past_messages[-HISTORY_WINDOW:]:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        content = m.content if isinstance(m.content, str) else str(m.content)
        lines.append(f"{role}: {content[:300]}")
    return "\n".join(lines)


# ── Node 1: Classify Intent ───────────────────────────────────────────────────

async def classify_intent(state: AgentState) -> AgentState:
    """
    Classify user intent and extract key travel parameters.

    FIX 2: Stale tool-data fields are reset here so they never bleed
            from a previous turn into the current one.
    """
    llm = get_llm()

    recent_history = _build_history_string(state)
    history_section = (
        f"\n\nPrevious conversation (use this to resolve references and "
        f"carry over destination/dates):\n{recent_history}"
        if recent_history else ""
    )

    classification_prompt = f"""You are a travel intent classifier. Analyze the user message and extract:
1. intent: one of [itinerary_planning, budget_estimation, weather_info, general_question, destination_research, greeting, unclear]
2. destination: city/country if mentioned (null if not). If not in current message, infer from conversation history ONLY if the current message is related to travel.
3. start_date: travel start date if mentioned in YYYY-MM-DD format (null if not)
4. end_date: travel end date if mentioned in YYYY-MM-DD format (null if not)
5. travelers: number of travelers if mentioned (null if not)
6. budget_range: budget preference if mentioned - "budget", "mid-range", or "luxury" (null if not)

Use general_question for non-travel questions (e.g. "Who are you?", "What is your name?", "Tell me a joke").
Use greeting for simple hellos/goodbyes.
Use destination_research when the user asks for attractions, landmarks, things to do, etc.

Respond ONLY with valid JSON. No explanation. Example:
{{"intent": "itinerary_planning", "destination": "Paris", "start_date": "2025-06-01", \
"end_date": "2025-06-07", "travelers": 2, "budget_range": "mid-range"}}{history_section}

Current user message: {state["user_query"]}"""

    # ── FIX 2: reset all stale per-turn data upfront ──────────────────────────
    clean_state: AgentState = {
        **state,
        # clear tool results from the previous turn
        "rag_context":    None,
        "weather_data":   None,
        "places_data":    None,
        "budget_data":    None,
        "itinerary_data": None,
        "travel_plan":    None,
        "final_response": None,
        "error":          None,
    }

    try:
        result = await invoke_with_retry(llm, [HumanMessage(content=classification_prompt)])

        # Normalise content to plain string
        raw = result.content
        if isinstance(raw, list):
            raw = "".join(
                c.get("text", "") if isinstance(c, dict) else str(c)
                for c in raw
            )
        raw = raw.strip()

        # Strip markdown fences if present
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        # Isolate the JSON object
        start_idx = raw.find("{")
        end_idx   = raw.rfind("}") + 1
        if start_idx >= 0 and end_idx > start_idx:
            raw = raw[start_idx:end_idx]

        parsed = json.loads(raw)

        # Coerce travelers to int safely
        travelers = parsed.get("travelers")
        if travelers is not None:
            try:
                if isinstance(travelers, str):
                    import re
                    match = re.search(r'\d+', travelers)
                    travelers = int(match.group()) if match else None
                else:
                    travelers = int(travelers)
            except (ValueError, TypeError):
                travelers = None

        return {
            **clean_state,
            "intent":       parsed.get("intent", "general_question"),
            "destination":  parsed.get("destination"),
            "start_date":   parsed.get("start_date"),
            "end_date":     parsed.get("end_date"),
            "travelers":    travelers,
            "budget_range": parsed.get("budget_range"),
        }

    except Exception as e:
        logger.warning(f"Intent classification error: {e}")
        return {**clean_state, "intent": "general_question"}


# ── Node 2: Gather Data (Parallel) ───────────────────────────────────────────

async def gather_data_node(state: AgentState) -> AgentState:
    """
    Run all necessary data-gathering tools in parallel based on intent.

    FIX 4: Returns early (no tool calls) for passive intents
            (general_question, greeting, unclear) even when a destination
            is present in state — prevents trip-formatted responses for
            simple conversational messages.
    """
    intent      = state.get("intent", "general_question")
    destination = state.get("destination")

    # ── FIX 4: skip ALL tools for passive intents ─────────────────────────────
    if intent in PASSIVE_INTENTS:
        logger.debug(f"[gather_data_node] Passive intent '{intent}' — skipping tools.")
        return state

    tasks:      List = []
    task_names: List[str] = []

    # RAG retrieval — always run for non-passive intents
    rag_query = f"{destination} {state['user_query']}" if destination else state["user_query"]
    tasks.append(retrieve_travel_info(rag_query))
    task_names.append("rag")

    if destination:
        if intent in WEATHER_INTENTS:
            tasks.append(get_weather_info(destination, state.get("start_date")))
            task_names.append("weather")

        if intent in PLACES_INTENTS:
            tasks.append(
                search_places_to_visit(
                    destination,
                    query=f"best places to visit in {destination}",
                )
            )
            task_names.append("places")

        if intent in BUDGET_INTENTS:
            tasks.append(
                estimate_budget(
                    destination=destination,
                    start_date=state.get("start_date"),
                    end_date=state.get("end_date"),
                    travelers=state.get("travelers") or 1,   # FIX 6
                    budget_range=state.get("budget_range", "mid-range"),
                )
            )
            task_names.append("budget")

    if not tasks:
        return state

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        new_state = {**state}
        for name, result in zip(task_names, results):
            if isinstance(result, Exception):
                logger.error(f"Error in parallel task '{name}': {result}")
                continue
            if   name == "rag":     new_state["rag_context"]  = result
            elif name == "weather": new_state["weather_data"]  = result
            elif name == "places":  new_state["places_data"]   = result
            elif name == "budget":  new_state["budget_data"]   = result
        return new_state

    except Exception as e:
        logger.error(f"Parallel gather error: {e}")
        return state


# ── Node 3: Itinerary Builder ─────────────────────────────────────────────────

async def itinerary_node(state: AgentState) -> AgentState:
    """Build a detailed day-by-day itinerary."""
    if not state.get("destination"):
        return state
    try:
        itinerary = await build_itinerary(
            destination=state["destination"],
            start_date=state.get("start_date"),
            end_date=state.get("end_date"),
            travelers=state.get("travelers") or 1,          # FIX 6
            budget_range=state.get("budget_range", "mid-range"),
            rag_context=state.get("rag_context", ""),
            places_context=format_places_for_prompt(state.get("places_data")),
        )
        return {**state, "itinerary_data": itinerary}
    except Exception as e:
        logger.warning(f"Itinerary tool error: {e}")
        return state


# ── Node 4: Synthesize Response ───────────────────────────────────────────────

async def synthesize_response(state: AgentState) -> AgentState:
    """
    Synthesize all gathered data into a final polished response.

    FIX 1: HumanMessage is now added alongside the AIMessage so the
            conversation history is complete for the next turn.
    FIX 3: Context injection is gated on intent — general/greeting
            questions get a clean system prompt with no tool context,
            preventing them from being formatted as trip plans.
    FIX 5: History window uses the same HISTORY_WINDOW constant as
            classify_intent for consistency.
    """
    llm    = get_llm()
    intent = state.get("intent", "general_question")

    # ── Build gathered context (only for non-passive intents) ─────────────────
    context_parts: List[str] = []

    has_itinerary = bool(state.get("itinerary_data"))

    if state.get("rag_context") and not has_itinerary:
        context_parts.append(f"## Travel Knowledge Base\n{state['rag_context']}")

    if state.get("weather_data"):
        context_parts.append(f"## Weather Data\n{json.dumps(state['weather_data'])}")

    if state.get("places_data") and not has_itinerary:
        places_str = format_places_for_prompt(state.get("places_data"))
        context_parts.append(f"## Google Places Recommendations\n{places_str}")

    if state.get("budget_data"):
        context_parts.append(f"## Budget Estimation\n{json.dumps(state['budget_data'])}")

    if state.get("itinerary_data"):
        context_parts.append(f"## Itinerary Plan\n{json.dumps(state['itinerary_data'])}")

    gathered_context = "\n\n".join(context_parts) if context_parts else ""

    MAX_CONTEXT_CHARS = 6000
    if len(gathered_context) > MAX_CONTEXT_CHARS:
        gathered_context = gathered_context[:MAX_CONTEXT_CHARS] + "\n...[context truncated]"

    # ── FIX 3: gate context injection on intent ───────────────────────────────
    if intent in PASSIVE_INTENTS or not gathered_context:
        # Plain assistant — no tool data injected, avoids trip-plan formatting
        system_message = SystemMessage(content=SYSTEM_PROMPT)
    else:
        system_message = SystemMessage(
            content=(
                f"{SYSTEM_PROMPT}\n\n"
                f"Use the following gathered data to craft your response:\n\n"
                f"{gathered_context}"
            )
        )

    # ── Build message list (system + recent history + current query) ──────────
    messages: List[BaseMessage] = [system_message]

    past_messages = state.get("messages", [])
    for m in past_messages[-HISTORY_WINDOW:]:          # FIX 5: consistent window
        messages.append(m)

    messages.append(HumanMessage(content=state["user_query"]))

    try:
        result   = await invoke_with_retry(llm, messages)
        response = result.content
        if isinstance(response, list):
            response = "".join(
                c.get("text", "") if isinstance(c, dict) else str(c)
                for c in response
            )

        # Build structured travel plan only when meaningful data exists
        travel_plan = None
        if state.get("destination") and (
            state.get("itinerary_data") or state.get("budget_data")
        ):
            travel_plan = {
                "destination":         state["destination"],
                "start_date":          state.get("start_date"),
                "end_date":            state.get("end_date"),
                "itinerary":           state.get("itinerary_data"),
                "budget":              state.get("budget_data"),
                "weather_info":        state.get("weather_data"),
                "places":              state.get("places_data"),
                "estimated_cost_usd": (
                    state["budget_data"].get("total_usd")
                    if state.get("budget_data") else None
                ),
            }

        return {
            **state,
            "final_response": response,
            "travel_plan":    travel_plan,
            # ── FIX 1: persist BOTH the human query and the AI reply ──────────
            "messages": [
                HumanMessage(content=state["user_query"]),
                AIMessage(content=response),
            ],
        }

    except Exception as e:
        import traceback
        logger.error(f"Synthesis error: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())
        error_msg = (
            "I apologize, I encountered an error processing your request. "
            "Please try again."
        )
        return {
            **state,
            "final_response": error_msg,
            "error":          str(e),
            # Still save the human message so history stays consistent
            "messages": [HumanMessage(content=state["user_query"])],
        }


# ── Routers ───────────────────────────────────────────────────────────────────

def intent_router(state: AgentState) -> str:
    """Route straight to synthesis for passive intents; otherwise gather data first."""
    if state.get("intent") in PASSIVE_INTENTS:
        return "synthesize_response"
    return "gather_data_node"


def post_gather_router(state: AgentState) -> str:
    """After gathering, build an itinerary only when explicitly requested."""
    if state.get("intent") == "itinerary_planning":
        return "itinerary_node"
    return "synthesize_response"


# ── Build Graph ───────────────────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("classify_intent",    classify_intent)
    workflow.add_node("gather_data_node",   gather_data_node)
    workflow.add_node("itinerary_node",     itinerary_node)
    workflow.add_node("synthesize_response", synthesize_response)

    workflow.set_entry_point("classify_intent")

    workflow.add_conditional_edges(
        "classify_intent",
        intent_router,
        {
            "gather_data_node":    "gather_data_node",
            "synthesize_response": "synthesize_response",
        },
    )

    workflow.add_conditional_edges(
        "gather_data_node",
        post_gather_router,
        {
            "itinerary_node":      "itinerary_node",
            "synthesize_response": "synthesize_response",
        },
    )

    workflow.add_edge("itinerary_node",     "synthesize_response")
    workflow.add_edge("synthesize_response", END)

    return workflow.compile()



# ── Singleton compiled graph ──────────────────────────────────────────────────

_agent_graph = None

def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph