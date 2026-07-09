from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Time, ForeignKey, func
from app.database.connection import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), nullable=True)
    summary = Column(Text)
    discussion = Column(Text)
    products = Column(Text)
    competitors = Column(Text)
    sentiment = Column(String(50))
    interest_level = Column(String(50))
    interaction_date = Column(Date)
    follow_up_date = Column(Date, nullable=True)
    duration = Column(Integer)
    interaction_type = Column(String(50))
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(), default=func.now())
    updated_at = Column(DateTime(), default=func.now(), onupdate=func.now())
