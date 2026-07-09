from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date


class RecentActivity(BaseModel):
    id: int
    doctor_name: Optional[str] = None
    interaction_type: Optional[str] = None
    hospital: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None


class UpcomingFollowUp(BaseModel):
    id: int
    doctor_name: Optional[str] = None
    follow_up_date: Optional[date] = None
    interest_level: Optional[str] = None


class DashboardResponse(BaseModel):
    total_hcps: int
    interactions_today: int
    pending_followups: int
    weekly_meetings: int
    weekly_activity: List[Dict[str, Any]]
    recent_activities: List[RecentActivity]
    upcoming_followups: List[UpcomingFollowUp]
