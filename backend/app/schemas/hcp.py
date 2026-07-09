from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class HCPCreate(BaseModel):
    doctor_name: str
    hospital: Optional[str] = None
    speciality: Optional[str] = None
    city: Optional[str] = None


class HCPResponse(BaseModel):
    id: int
    doctor_name: str
    hospital: Optional[str]
    speciality: Optional[str]
    city: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
