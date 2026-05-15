from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[int] = None  # If None, creates a new session


class ChatResponse(BaseModel):
    session_id: int
    session_title: str
    response: str
    travel_plan_id: Optional[int] = None  # Set if agent created a plan


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    message_count: int = 0
    travel_plan_id: Optional[int] = None

    model_config = {"from_attributes": True}


class SessionDetailResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: List[MessageResponse]
    travel_plan_id: Optional[int] = None

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    total: int
    sessions: List[SessionResponse]
