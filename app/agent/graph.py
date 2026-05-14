"""
LangGraph Travel Planner Agent
==============================
Multi-step stateful agent that:
1. Classifies user intent
2. Routes to specialized tool nodes (RAG, weather, budget, itinerary)
3. Synthesizes a final, structured response
4. Persists the trip plan if applicable
"""

from typing import TypedDict, Annotated, List, Optional, Any, Dict
from datetime import datetime
import operator
import json

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


# Agent State
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    user_query: str
    intent: Optional[str]           # classified intent
    destination: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    travelers: Optional[int]
    budget_range: Optional[str]     # "budget" | "mid-range" | "luxury"
    rag_context: Optional[str]
    weather_data: Optional[Dict]
    places_data: Optional[Dict]
    budget_data: Optional[Dict]
    itinerary_data: Optional[Dict]
    final_response: Optional[str]
    travel_plan: Optional[Dict]     # structured plan to save to DB
    error: Optional[str]


# System Prompt
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
Do NOT escape new lines (no \n in output).
Use proper Markdown syntax:
- Headings using #
- Bold using **
- Lists using numbers or -
Ensure output is formatted for direct rendering in UI, not as a JSON string."""


# Node: Classify Intent
async def classify_intent(state: AgentState) -> AgentState:
    """Classify user intent and extract key travel parameters."""
    llm = get_llm()

    classification_prompt = f"""You are a travel intent classifier. Analyze the user message and extract:
1. intent: one of [itinerary_planning, budget_estimation, weather_info, general_question, destination_research, greeting, unclear]
2. destination: city/country if mentioned (null if not)
3. start_date: travel start date if mentioned in YYYY-MM-DD format (null if not)
4. end_date: travel end date if mentioned in YYYY-MM-DD format (null if not)
5. travelers: number of travelers if mentioned (null if not)
6. budget_range: budget preference if mentioned - "budget", "mid-range", or "luxury" (null if not)

Use destination_research when the user asks for attractions, landmarks, things to do, places to visit, restaurants, museums, activities, or destination recommendations without asking for a full day-by-day itinerary.

Respond ONLY with valid JSON. No explanation. Example:
{{"intent": "itinerary_planning", "destination": "Paris", "start_date": "2025-06-01", "end_date": "2025-06-07", "travelers": 2, "budget_range": "mid-range"}}

User message: {state["user_query"]}"""

    try:
        result = await llm.ainvoke([HumanMessage(content=classification_prompt)])

        # Ensure content is string
        raw = result.content
        if isinstance(raw, list):
            raw = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in raw])
        raw = raw.strip()

        # Extract JSON from possible markdown fences
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        # Find JSON object boundaries
        start_idx = raw.find("{")
        end_idx = raw.rfind("}") + 1
        if start_idx >= 0 and end_idx > start_idx:
            raw = raw[start_idx:end_idx]

        parsed = json.loads(raw)

        # Ensure travelers is int
        travelers = parsed.get("travelers")
        if travelers is not None:
            try:
                if isinstance(travelers, str):
                    import re
                    match = re.search(r'\d+', travelers)
                    travelers = int(match.group()) if match else 1
                else:
                    travelers = int(travelers)
            except (ValueError, TypeError):
                travelers = 1

        return {
            **state,
            "intent": parsed.get("intent", "general_question"),
            "destination": parsed.get("destination"),
            "start_date": parsed.get("start_date"),
            "end_date": parsed.get("end_date"),
            "travelers": travelers,
            "budget_range": parsed.get("budget_range"),
        }
    except Exception as e:
        logger.warning(f"Intent classification error: {e}")
        return {**state, "intent": "general_question"}


# Node: RAG Retrieval
async def rag_retrieval(state: AgentState) -> AgentState:
    """Retrieve relevant travel information from the knowledge base."""
    try:
        query = state["user_query"]
        if state.get("destination"):
            query = f"{state['destination']} {query}"

        context = await retrieve_travel_info(query)
        return {**state, "rag_context": context}
    except Exception as e:
        logger.warning(f"RAG retrieval error: {e}")
        return {**state, "rag_context": ""}


# Node: Weather Tool
async def weather_node(state: AgentState) -> AgentState:
    """Fetch weather information for the destination."""
    if not state.get("destination"):
        return state

    try:
        weather = await get_weather_info(state["destination"], state.get("start_date"))
        return {**state, "weather_data": weather}
    except Exception as e:
        logger.warning(f"Weather tool error: {e}")
        return state


# Node: Budget Estimation
async def places_node(state: AgentState) -> AgentState:
    """Fetch live attractions and places to visit for the destination."""
    if not state.get("destination"):
        return state

    try:
        query = f"best places to visit in {state['destination']}"
        places = await search_places_to_visit(state["destination"], query=query)
        return {**state, "places_data": places}
    except Exception as e:
        logger.warning(f"Google Places tool error: {e}")
        return state


async def budget_node(state: AgentState) -> AgentState:
    """Estimate travel budget based on destination and preferences."""
    if not state.get("destination"):
        return state

    try:
        budget = await estimate_budget(
            destination=state["destination"],
            start_date=state.get("start_date"),
            end_date=state.get("end_date"),
            travelers=state.get("travelers", 1),
            budget_range=state.get("budget_range", "mid-range"),
        )
        return {**state, "budget_data": budget}
    except Exception as e:
        logger.warning(f"Budget tool error: {e}")
        return state


# Node: Itinerary Builder
async def itinerary_node(state: AgentState) -> AgentState:
    """Build a detailed day-by-day itinerary."""
    if not state.get("destination"):
        return state

    try:
        itinerary = await build_itinerary(
            destination=state["destination"],
            start_date=state.get("start_date"),
            end_date=state.get("end_date"),
            travelers=state.get("travelers", 1),
            budget_range=state.get("budget_range", "mid-range"),
            rag_context=state.get("rag_context", ""),
            places_context=format_places_for_prompt(state.get("places_data")),
        )
        return {**state, "itinerary_data": itinerary}
    except Exception as e:
        logger.warning(f"Itinerary tool error: {e}")
        return state


# Node: Synthesize Response
async def synthesize_response(state: AgentState) -> AgentState:
    """Synthesize all gathered data into a final polished response."""
    llm = get_llm()

    # Build context for synthesis
    context_parts = []

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

    gathered_context = "\n\n".join(context_parts) if context_parts else "No additional data gathered."

    # Build conversation history string (last 6 messages)
    history_text = ""
    past_messages = state.get("messages", [])[-6:]
    if past_messages:
        history_lines = []
        for m in past_messages:
            role = "User" if isinstance(m, HumanMessage) else "Assistant"
            content = m.content if isinstance(m.content, str) else str(m.content)
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)

    # Single prompt string — Groq works best with simple message lists
    system_message = f"""{SYSTEM_PROMPT}

Use the following gathered data to craft your response:

{gathered_context}"""

    user_message = ""
    if history_text:
        user_message += f"Previous conversation:\n{history_text}\n\n"
    user_message += f"Current question: {state['user_query']}"

    try:
        result = await llm.ainvoke([
            SystemMessage(content=system_message),
            HumanMessage(content=user_message),
        ])

        # Ensure content is string
        response = result.content
        if isinstance(response, list):
            response = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in response])

        # Build travel plan if we have enough data
        travel_plan = None
        if state.get("destination") and (state.get("itinerary_data") or state.get("budget_data")):
            travel_plan = {
                "destination": state["destination"],
                "start_date": state.get("start_date"),
                "end_date": state.get("end_date"),
                "itinerary": state.get("itinerary_data"),
                "budget": state.get("budget_data"),
                "weather_info": state.get("weather_data"),
                "places": state.get("places_data"),
                "estimated_cost_usd": (
                    state["budget_data"].get("total_usd")
                    if state.get("budget_data") else None
                ),
            }

        return {
            **state,
            "final_response": response,
            "travel_plan": travel_plan,
            "messages": state.get("messages", []) + [AIMessage(content=response)],
        }

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        error_msg = "I apologize, I encountered an error processing your request. Please try again."
        return {**state, "final_response": error_msg, "error": str(e)}


# Router: classify → next node
def intent_router(state: AgentState) -> str:
    """After intent classification, route to RAG or directly to synthesis."""
    intent = state.get("intent", "general_question")
    if intent == "greeting":
        return "synthesize_response"
    return "rag_retrieval"


# Router: rag → next node
def tool_router(state: AgentState) -> str:
    """After RAG retrieval, decide which tool chain to run."""
    intent = state.get("intent", "general_question")
    if intent == "weather_info":
        return "weather_node"
    if intent == "destination_research":
        return "places_node"
    if intent in ("budget_estimation", "itinerary_planning"):
        return "weather_node"
    return "synthesize_response"


# Router: budget → next node
def weather_router(state: AgentState) -> str:
    """After weather, continue planning or finish weather-only requests."""
    if state.get("intent") == "weather_info":
        return "synthesize_response"
    if state.get("intent") == "itinerary_planning":
        return "places_node"
    return "budget_node"


def places_router(state: AgentState) -> str:
    """After live place search, continue itinerary planning or synthesize."""
    if state.get("intent") == "itinerary_planning":
        return "budget_node"
    return "synthesize_response"


def budget_router(state: AgentState) -> str:
    """After budget estimation, go to itinerary if planning, else synthesize."""
    if state.get("intent") == "itinerary_planning":
        return "itinerary_node"
    return "synthesize_response"


# Build Graph
def build_agent_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("rag_retrieval", rag_retrieval)
    workflow.add_node("weather_node", weather_node)
    workflow.add_node("places_node", places_node)
    workflow.add_node("budget_node", budget_node)
    workflow.add_node("itinerary_node", itinerary_node)
    workflow.add_node("synthesize_response", synthesize_response)

    # Entry point
    workflow.set_entry_point("classify_intent")

    # classify_intent → (greeting → synthesis | everything else → rag)
    workflow.add_conditional_edges(
        "classify_intent",
        intent_router,
        {
            "synthesize_response": "synthesize_response",
            "rag_retrieval": "rag_retrieval",
        },
    )

    # rag_retrieval → (weather | synthesis)
    workflow.add_conditional_edges(
        "rag_retrieval",
        tool_router,
        {
            "weather_node": "weather_node",
            "places_node": "places_node",
            "synthesize_response": "synthesize_response",
        },
    )

    workflow.add_conditional_edges(
        "weather_node",
        weather_router,
        {
            "places_node": "places_node",
            "budget_node": "budget_node",
            "synthesize_response": "synthesize_response",
        },
    )

    workflow.add_conditional_edges(
        "places_node",
        places_router,
        {
            "budget_node": "budget_node",
            "synthesize_response": "synthesize_response",
        },
    )

    # budget_node → (itinerary | synthesis)  — ONE conditional edge only
    workflow.add_conditional_edges(
        "budget_node",
        budget_router,
        {
            "itinerary_node": "itinerary_node",
            "synthesize_response": "synthesize_response",
        },
    )

    # itinerary_node → synthesis
    workflow.add_edge("itinerary_node", "synthesize_response")

    # synthesis → END
    workflow.add_edge("synthesize_response", END)

    return workflow.compile()


# Singleton compiled graph
_agent_graph = None


def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        logger.info("[AGENT] Compiling LangGraph agent...")
        _agent_graph = build_agent_graph()
        logger.info("[AGENT] Agent graph ready.")
    return _agent_graph
