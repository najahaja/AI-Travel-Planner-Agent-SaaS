from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import date, datetime


class TravelPlanResponse(BaseModel):
    id: int
    user_id: int
    user_email: Optional[str] = None
    destination: str
    start_date: Optional[date]
    end_date: Optional[date]
    itinerary: Optional[Dict[str, Any]]
    budget: Optional[Dict[str, Any]]
    weather_info: Optional[Dict[str, Any]]
    notes: Optional[str]
    estimated_cost_usd: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TravelPlanListResponse(BaseModel):
    total: int
    plans: list[TravelPlanResponse]


class SuperAdminAnalytics(BaseModel):
    total_admins: int
    total_users: int
    total_conversations: int
    total_travel_plans: int
    active_users_last_7_days: int
