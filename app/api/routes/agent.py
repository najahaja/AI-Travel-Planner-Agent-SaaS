"""Agent / chat routes — user-facing travel planning endpoint."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
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

from app.core.limiter import limiter
from app.core.config import settings

router = APIRouter(prefix="/agent", tags=["Travel Agent"])


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def chat(
    request: Request,
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

        # Load only the last 20 messages (10 turns) to avoid token overflow
        msg_result = await db.execute(
            select(Message)
            .where(Message.session_id == session.id)
            .order_by(Message.timestamp.desc())
            .limit(20)
        )
        db_messages = list(reversed(msg_result.scalars().all()))
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

    # 5. Save/Update travel plan if generated
    travel_plan_id = None
    if final_state.get("travel_plan"):
        plan_data = final_state["travel_plan"]
        
        # Check if a plan already exists for this session
        plan_result = await db.execute(
            select(TravelPlan).where(TravelPlan.session_id == session.id)
        )
        plan = plan_result.scalars().first()
        
        if not plan:
            plan = TravelPlan(
                user_id=current_user.id,
                session_id=session.id,
                destination=plan_data.get("destination", "Unknown"),
            )
            db.add(plan)
        
        # Update plan details
        plan.destination = plan_data.get("destination", "Unknown")
        plan.itinerary = plan_data.get("itinerary")
        plan.budget = plan_data.get("budget")
        plan.weather_info = plan_data.get("weather_info")
        plan.estimated_cost_usd = plan_data.get("estimated_cost_usd")
        plan.notes = f"Updated from chat session {session.id}"

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
    # Subquery for message count
    message_count_sub = (
        select(Message.session_id, func.count(Message.id).label("count"))
        .group_by(Message.session_id)
        .subquery()
    )

    query = (
        select(
            ChatSession,
            func.coalesce(message_count_sub.c.count, 0).label("message_count"),
            func.max(TravelPlan.id).label("travel_plan_id")
        )
        .outerjoin(message_count_sub, message_count_sub.c.session_id == ChatSession.id)
        .outerjoin(TravelPlan, TravelPlan.session_id == ChatSession.id)
        .where(ChatSession.user_id == current_user.id)
        .group_by(ChatSession.id)
        .order_by(ChatSession.created_at.desc())
    )
    result = await db.execute(query)
    sessions_data = result.all()

    return SessionListResponse(
        total=len(sessions_data),
        sessions=[
            SessionResponse(
                id=s.ChatSession.id,
                title=s.ChatSession.title,
                created_at=s.ChatSession.created_at,
                message_count=s.message_count,
                travel_plan_id=s.travel_plan_id
            )
            for s in sessions_data
        ],
    )


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

    # Find associated travel plan
    plan_result = await db.execute(
        select(TravelPlan.id).where(TravelPlan.session_id == session.id)
    )
    travel_plan_id = plan_result.scalar_one_or_none()

    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        messages=[MessageResponse.model_validate(m) for m in messages],
        travel_plan_id=travel_plan_id
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
    """List all saved travel plans. Role-aware: SuperAdmin (all), Admin (managed users), User (own)."""
    from app.models.user import UserRole, User
    
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super Admin sees everything
        query = select(TravelPlan)
    elif current_user.role == UserRole.ADMIN:
        # Admin sees their own trips + trips of users they manage
        # Subquery to get managed user IDs
        managed_user_ids_sub = select(User.id).where(User.admin_id == current_user.id)
        query = select(TravelPlan).where(
            (TravelPlan.user_id == current_user.id) | 
            (TravelPlan.user_id.in_(managed_user_ids_sub))
        )
    else:
        # Regular user only sees their own
        query = select(TravelPlan).where(TravelPlan.user_id == current_user.id)

    from sqlalchemy.orm import selectinload
    result = await db.execute(
        query.options(selectinload(TravelPlan.user)).order_by(TravelPlan.created_at.desc())
    )
    plans = result.scalars().all()
    
    response_plans = []
    for p in plans:
        resp = TravelPlanResponse.model_validate(p)
        resp.user_email = p.user.email if p.user else "Unknown"
        response_plans.append(resp)

    return TravelPlanListResponse(
        total=len(plans),
        plans=response_plans,
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
