from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class ValidationSession(Base):
    __tablename__ = "stakeholder_validation_sessions"

    id = Column(String, primary_key=True, index=True)
    participant_code = Column(String, nullable=True)
    stakeholder_role = Column(String, nullable=False)  # "rider", "dispatcher", "restaurant", "customer"
    validation_scenario = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    responses = relationship("ValidationResponse", back_populates="session", cascade="all, delete-orphan")


class ValidationResponse(Base):
    __tablename__ = "stakeholder_validation_responses"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("stakeholder_validation_sessions.id"), nullable=False)
    question_id = Column(String, nullable=False)  # "Q1" to "Q10"
    rating = Column(Integer, nullable=False)       # 1 to 5 Likert scale
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ValidationSession", back_populates="responses")
