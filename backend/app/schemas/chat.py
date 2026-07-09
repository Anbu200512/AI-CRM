from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    extracted: Dict[str, Any]
    tool_used: str
    conversation_id: str
    title: Optional[str] = None


class ExtractRequest(BaseModel):
    text: str


class ExtractResponse(BaseModel):
    doctor_name: Optional[str] = None
    hospital: Optional[str] = None
    speciality: Optional[str] = None
    interaction_date: Optional[str] = None
    meeting_duration: Optional[str] = None
    interaction_type: Optional[str] = None
    products_discussed: Optional[List[str]] = None
    competitor_products: Optional[List[str]] = None
    interest_level: Optional[str] = None
    follow_up_date: Optional[str] = None
    discussion_notes: Optional[str] = None
    sentiment: Optional[str] = None
    summary: Optional[str] = None


class FollowUpRequest(BaseModel):
    interaction_id: int
    summary: str


class FollowUpResponse(BaseModel):
    next_follow_up: str
    priority: str
    talking_points: List[str]
    suggested_products: List[str]
    reasoning: str
