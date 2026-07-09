from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List


class InteractionCreate(BaseModel):
    hcp_id: Optional[int] = None
    doctor_name: Optional[str] = None
    hospital: Optional[str] = None
    speciality: Optional[str] = None
    summary: Optional[str] = None
    discussion: Optional[str] = None
    products: Optional[str] = None
    competitors: Optional[str] = None
    sentiment: Optional[str] = None
    interest_level: Optional[str] = None
    interaction_date: date
    follow_up_date: Optional[date] = None
    duration: Optional[int] = None
    interaction_type: str = "structured"


class InteractionUpdate(BaseModel):
    summary: Optional[str] = None
    discussion: Optional[str] = None
    products: Optional[str] = None
    competitors: Optional[str] = None
    sentiment: Optional[str] = None
    interest_level: Optional[str] = None
    follow_up_date: Optional[date] = None
    duration: Optional[int] = None


class InteractionResponse(BaseModel):
    id: int
    hcp_id: Optional[int]
    summary: Optional[str]
    discussion: Optional[str]
    products: Optional[str]
    competitors: Optional[str]
    sentiment: Optional[str]
    interest_level: Optional[str]
    interaction_date: Optional[date]
    follow_up_date: Optional[date]
    duration: Optional[int]
    interaction_type: Optional[str]
    created_by: Optional[int]
    doctor_name: Optional[str] = None
    hospital: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InteractionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[InteractionResponse]
