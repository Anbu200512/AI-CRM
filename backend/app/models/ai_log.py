from sqlalchemy import Column, Integer, Text, String, Float, DateTime, func
from app.database.connection import Base


class AILog(Base):
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(Text)
    response = Column(Text)
    tool = Column(String(100))
    execution_time = Column(Float)
    timestamp = Column(DateTime(), default=func.now())
