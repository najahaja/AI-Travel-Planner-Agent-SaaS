"""Agent / chat routes — user-facing travel planning endpoint."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import require_user_or_above
from app.models.user import User
from app.models.chat import ChatSession, Message
from app.models.travel import TravelPlan
from app.schemas.chat import (
    ChatRequest, ChatResponse,
    SessionResponse, SessionDetailResponse, SessionListResponse,
    MessageResponse,
)
from app.schemas.travel import TravelPlanResponse, TravelPlanListResponse
from app.agent.graph import get_agent_graph, AgentState
# pyrefly: ignore [missing-import]
from langchain_core.messages import HumanMessage
# pyrefly: ignore [missing-import]
from loguru import logger
# pyrefly: ignore [missing-import]
from datetime import date

router = APIRouter(prefix="/agent", tags=["Travel Agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user_or_above),
):
    """
    Send a message to the AI Travel Planner Agent.
    Creates or continues a chat session.
    """
    # 1. Get or create session
    session = None
    history_messages = []

    if payload.session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == payload.session_id,
                ChatSession.user_id == current_user.id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Load message history
        msg_result = await db.execute(
            select(Message)
            .where(Message.session_id == session.id)
            .order_by(Message.timestamp)
        )
        db_messages = msg_result.scalars().all()
        for m in db_messages:
            if m.role == "user":
                history_messages.append(HumanMessage(content=m.content))
            else:
                # pyrefly: ignore [missing-import]
                from langchain_core.messages import AIMessage
                history_messages.append(AIMessage(content=m.content))

    # 2. Run agent
    agent = get_agent_graph()
    initial_state: AgentState = {
        "messages": history_messages,
        "user_query": payload.message,
        "intent": None,
        "destination": None,
        "start_date": None,
        "end_date": None,
        "travelers": None,
        "budget_range": None,
        "rag_context": None,
        "weather_data": None,
        "places_data": None,
        "budget_data": None,
        "itinerary_data": None,
        "final_response": None,
        "travel_plan": None,
        "error": None,
    }

    try:
        final_state = await agent.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"Agent error for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Agent processing failed. Please try again.")

    ai_response = final_state.get("final_response", "I encountered an issue. Please try again.")

    # 3. Create session if new
    if not session:
        title = payload.message[:80] + ("..." if len(payload.message) > 80 else "")
        session = ChatSession(user_id=current_user.id, title=title)
        db.add(session)
        await db.flush()  # Get session.id before adding messages

    # 4. Save messages
    user_msg = Message(session_id=session.id, role="user", content=payload.message)
    ai_msg = Message(session_id=session.id, role="assistant", content=ai_response)
    db.add(user_msg)
    db.add(ai_msg)

    # 5. Save travel plan if generated
    travel_plan_id = None
    if final_state.get("travel_plan"):
        plan_data = final_state["travel_plan"]
        plan = TravelPlan(
            user_id=current_user.id,
            destination=plan_data.get("destination", "Unknown"),
            itinerary=plan_data.get("itinerary"),
            budget=plan_data.get("budget"),
            weather_info=plan_data.get("weather_info"),
            estimated_cost_usd=plan_data.get("estimated_cost_usd"),
            notes=f"Generated from chat session {session.id}",
        )
        # Parse dates if available
        if plan_data.get("start_date"):
            try:
                plan.start_date = date.fromisoformat(plan_data["start_date"])
            except Exception:
                pass
        if plan_data.get("end_date"):
            try:
                plan.end_date = date.fromisoformat(plan_data["end_date"])
            except Exception:
                pass

        db.add(plan)
        await db.flush()  # Get plan.id
        travel_plan_id = plan.id

    # Commit everything: session, messages, and optional travel plan
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"DB commit failed for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save chat history. Please try again.")

    return ChatResponse(
        session_id=session.id,
        session_title=session.title,
        response=ai_response,
        travel_plan_id=travel_plan_id,
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user_or_above),
):
    """List all chat sessions for current user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
    )
    sessions = result.scalars().all()

    session_responses = []
    for s in sessions:
        count_result = await db.scalar(
            select(func.count(Message.id)).where(Message.session_id == s.id)
        )
        session_responses.append(
            SessionResponse(
                id=s.id,
                title=s.title,
                created_at=s.created_at,
                message_count=count_result or 0,
            )
        )

    return SessionListResponse(total=len(session_responses), sessions=session_responses)


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user_or_above),
):
    """Get full chat history for a session."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await db.execute(
        select(Message).where(Message.session_id == session.id).order_by(Message.timestamp)
    )
    messages = msg_result.scalars().all()

    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user_or_above),
):
    """Delete a chat session and all its messages."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()


@router.get("/trips", response_model=TravelPlanListResponse)
async def list_trips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user_or_above),
):
    """List all saved travel plans for current user."""
    result = await db.execute(
        select(TravelPlan)
        .where(TravelPlan.user_id == current_user.id)
        .order_by(TravelPlan.created_at.desc())
    )
    plans = result.scalars().all()
    return TravelPlanListResponse(
        total=len(plans),
        plans=[TravelPlanResponse.model_validate(p) for p in plans],
    )


@router.get("/trips/{trip_id}", response_model=TravelPlanResponse)
async def get_trip(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user_or_above),
):
    """Get detailed travel plan."""
    result = await db.execute(
        select(TravelPlan).where(
            TravelPlan.id == trip_id,
            TravelPlan.user_id == current_user.id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found")
    return TravelPlanResponse.model_validate(plan)
