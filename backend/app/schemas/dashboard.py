from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date


class DashboardStats(BaseModel):
    total_hcps: int
    interactions_today: int
    pending_followups: int
    weekly_meetings: int


class RecentActivity(BaseModel):
    id: int
    doctor_name: Optional[str] = None
    interaction_type: Optional[str] = None
    created_at: Optional[str] = None


class UpcomingFollowUp(BaseModel):
    id: int
    doctor_name: Optional[str] = None
    follow_up_date: Optional[date] = None
    interest_level: Optional[str] = None


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_activities: List[RecentActivity]
    upcoming_followups: List[UpcomingFollowUp]
    weekly_data: List[Dict[str, Any]]
    monthly_data: List[Dict[str, Any]]
