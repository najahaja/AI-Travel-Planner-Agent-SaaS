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

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

from app.agent.llm import get_llm
from app.agent.tools.weather import get_weather_info
from app.agent.tools.budget import estimate_budget
from app.agent.tools.itinerary import build_itinerary
from app.agent.tools.currency import convert_currency
from app.rag.retriever import retrieve_travel_info
from loguru import logger


# ── Agent State ────────────────────────────────────────────────────────────────
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
    budget_data: Optional[Dict]
    itinerary_data: Optional[Dict]
    currency_data: Optional[Dict]
    final_response: Optional[str]
    travel_plan: Optional[Dict]     # structured plan to save to DB
    error: Optional[str]


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert AI Travel Planner with deep knowledge of global destinations, 
travel logistics, budgeting, cultural insights, and itinerary design.

Your capabilities:
- Create detailed day-by-day itineraries
- Estimate realistic budgets (flights, hotels, food, activities)
- Provide weather insights and best travel times
- Offer visa requirements and travel advisories
- Recommend hidden gems and off-the-beaten-path experiences
- Convert currencies and provide cost comparisons
- Answer questions using a knowledge base of travel guides

Always respond in a professional, helpful, and enthusiastic manner.
When planning a trip, always ask for: destination, travel dates, number of travelers, and budget preference if not provided.
Structure your responses clearly with headers and bullet points.
"""

# ── Node: Classify Intent ──────────────────────────────────────────────────────
async def classify_intent(state: AgentState) -> AgentState:
    """Classify user intent and extract key travel parameters."""
    llm = get_llm()

    classification_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a travel intent classifier. Analyze the user message and extract:
1. intent: one of [itinerary_planning, budget_estimation, weather_info, general_question, destination_research, greeting, unclear]
2. destination: city/country if mentioned (null if not)
3. start_date: travel start date if mentioned (null if not)
4. end_date: travel end date if mentioned (null if not)
5. travelers: number of travelers if mentioned (null if not)
6. budget_range: budget preference if mentioned - "budget", "mid-range", or "luxury" (null if not)

Respond ONLY with valid JSON like:
{{"intent": "itinerary_planning", "destination": "Paris", "start_date": "2025-06-01", "end_date": "2025-06-07", "travelers": 2, "budget_range": "mid-range"}}
"""),
        ("human", "{query}"),
    ])

    try:
        chain = classification_prompt | llm
        result = await chain.ainvoke({"query": state["user_query"]})
        raw = result.content.strip()

        # Extract JSON
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        parsed = json.loads(raw)

        return {
            **state,
            "intent": parsed.get("intent", "general_question"),
            "destination": parsed.get("destination"),
            "start_date": parsed.get("start_date"),
            "end_date": parsed.get("end_date"),
            "travelers": parsed.get("travelers"),
            "budget_range": parsed.get("budget_range"),
        }
    except Exception as e:
        logger.warning(f"Intent classification error: {e}")
        return {**state, "intent": "general_question"}


# ── Node: RAG Retrieval ────────────────────────────────────────────────────────
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


# ── Node: Weather Tool ─────────────────────────────────────────────────────────
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


# ── Node: Budget Estimation ────────────────────────────────────────────────────
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


# ── Node: Itinerary Builder ────────────────────────────────────────────────────
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
        )
        return {**state, "itinerary_data": itinerary}
    except Exception as e:
        logger.warning(f"Itinerary tool error: {e}")
        return state


# ── Node: Synthesize Response ──────────────────────────────────────────────────
async def synthesize_response(state: AgentState) -> AgentState:
    """Synthesize all gathered data into a final polished response."""
    llm = get_llm()

    # Build context for synthesis
    context_parts = []

    if state.get("rag_context"):
        context_parts.append(f"## Travel Knowledge Base\n{state['rag_context']}")

    if state.get("weather_data"):
        context_parts.append(f"## Weather Data\n{json.dumps(state['weather_data'], indent=2)}")

    if state.get("budget_data"):
        context_parts.append(f"## Budget Estimation\n{json.dumps(state['budget_data'], indent=2)}")

    if state.get("itinerary_data"):
        context_parts.append(f"## Itinerary Plan\n{json.dumps(state['itinerary_data'], indent=2)}")

    gathered_context = "\n\n".join(context_parts)

    synthesis_prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("system", f"Use the following data to craft your response:\n\n{gathered_context}" if gathered_context else ""),
        *[("human" if isinstance(m, HumanMessage) else "assistant", m.content)
          for m in state.get("messages", [])[-6:]],  # Last 6 messages for context
        ("human", "{query}"),
    ])

    try:
        chain = synthesis_prompt | llm
        result = await chain.ainvoke({"query": state["user_query"]})
        response = result.content

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


# ── Router: Intent → Nodes ────────────────────────────────────────────────────
def route_by_intent(state: AgentState) -> List[str]:
    """Determine which tool nodes to run based on classified intent."""
    intent = state.get("intent", "general_question")

    if intent == "itinerary_planning":
        return ["rag_retrieval", "weather_node", "budget_node", "itinerary_node"]
    elif intent == "budget_estimation":
        return ["rag_retrieval", "budget_node"]
    elif intent == "weather_info":
        return ["weather_node"]
    elif intent in ["destination_research", "general_question"]:
        return ["rag_retrieval"]
    elif intent == "greeting":
        return []
    else:
        return ["rag_retrieval"]


# ── Build Graph ────────────────────────────────────────────────────────────────
def build_agent_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("rag_retrieval", rag_retrieval)
    workflow.add_node("weather_node", weather_node)
    workflow.add_node("budget_node", budget_node)
    workflow.add_node("itinerary_node", itinerary_node)
    workflow.add_node("synthesize_response", synthesize_response)

    # Entry → classify
    workflow.set_entry_point("classify_intent")

    # After classification, fan out to relevant tools then converge to synthesis
    # We use a sequential approach: classify → rag → weather → budget → itinerary → synthesize
    # (nodes are skipped if intent doesn't require them)
    workflow.add_edge("classify_intent", "rag_retrieval")
    workflow.add_edge("rag_retrieval", "weather_node")
    workflow.add_edge("weather_node", "budget_node")
    workflow.add_edge("budget_node", "itinerary_node")
    workflow.add_edge("itinerary_node", "synthesize_response")
    workflow.add_edge("synthesize_response", END)

    return workflow.compile()


# Singleton compiled graph
_agent_graph = None


def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph
