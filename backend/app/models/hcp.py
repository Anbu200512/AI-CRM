from sqlalchemy import Column, Integer, String, DateTime, func
from app.database.connection import Base


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    doctor_name = Column(String(255), nullable=False, index=True)
    hospital = Column(String(255))
    speciality = Column(String(255))
    city = Column(String(255))
    created_at = Column(DateTime(), default=func.now())
