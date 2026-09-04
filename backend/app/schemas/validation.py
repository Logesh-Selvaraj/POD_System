from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class ValidationSessionCreate(BaseModel):
    participant_code: Optional[str] = None
    stakeholder_role: str = Field(..., description="Role of the participant, e.g. rider, dispatcher, restaurant, customer")
    validation_scenario: str = Field(..., description="Details of the scenario task executed")


class ValidationSessionResponse(BaseModel):
    id: str
    participant_code: Optional[str]
    stakeholder_role: str
    validation_scenario: str
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ValidationResponseCreate(BaseModel):
    session_id: str
    question_id: str = Field(..., pattern="^Q(10|[1-9])$", description="Question code from Q1 to Q10")
    rating: int = Field(..., ge=1, le=5, description="Likert score rating from 1 to 5")
    comment: Optional[str] = None


class ValidationResponseOut(BaseModel):
    id: str
    session_id: str
    question_id: str
    rating: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionRating(BaseModel):
    question_id: str
    average_rating: float


class RoleRating(BaseModel):
    role: str
    average_rating: float


class FeedbackComment(BaseModel):
    role: str
    comment: str
    question_id: str


class ValidationSummaryResponse(BaseModel):
    total_participants: int
    completed_sessions: int
    average_overall_rating: float
    average_rating_per_question: List[QuestionRating]
    average_rating_by_role: List[RoleRating]
    completion_rate: float
    comments: List[FeedbackComment]
    difficulty_areas: List[str]
