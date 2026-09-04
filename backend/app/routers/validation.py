import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.validation import ValidationSession, ValidationResponse
from app.dependencies import RequireRole
from app.schemas.validation import (
    ValidationSessionCreate,
    ValidationSessionResponse,
    ValidationResponseCreate,
    ValidationResponseOut,
    ValidationSummaryResponse,
    QuestionRating,
    RoleRating,
    FeedbackComment
)

router = APIRouter(prefix="/validation", tags=["Stakeholder Validation"])

VALID_ROLES = ["rider", "dispatcher", "restaurant", "customer"]

@router.post("/sessions", response_model=ValidationSessionResponse, status_code=status.HTTP_201_CREATED)
def create_validation_session(
    session_in: ValidationSessionCreate,
    db: Session = Depends(get_db)
):
    role_lower = session_in.stakeholder_role.lower()
    if role_lower not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid stakeholder role '{session_in.stakeholder_role}'. Must be one of {VALID_ROLES}."
        )

    session = ValidationSession(
        id=str(uuid.uuid4()),
        participant_code=session_in.participant_code,
        stakeholder_role=role_lower,
        validation_scenario=session_in.validation_scenario,
        started_at=datetime.utcnow()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/responses", response_model=ValidationResponseOut, status_code=status.HTTP_201_CREATED)
def submit_validation_response(
    response_in: ValidationResponseCreate,
    db: Session = Depends(get_db)
):
    # 1. Verify session exists
    session = db.query(ValidationSession).filter(ValidationSession.id == response_in.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation session '{response_in.session_id}' not found."
        )

    # 2. Verify rating boundaries
    if response_in.rating < 1 or response_in.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rating must be between 1 and 5."
        )

    # 3. Verify question format
    q_num = response_in.question_id
    if not q_num.startswith("Q") or not q_num[1:].isdigit() or int(q_num[1:]) < 1 or int(q_num[1:]) > 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question ID must be in range Q1 to Q10."
        )

    response = ValidationResponse(
        id=str(uuid.uuid4()),
        session_id=response_in.session_id,
        question_id=response_in.question_id,
        rating=response_in.rating,
        comment=response_in.comment,
        created_at=datetime.utcnow()
    )
    db.add(response)

    # Mark session completed_at on submission
    if not session.completed_at:
        session.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(response)
    return response


@router.get("/admin/summary", response_model=ValidationSummaryResponse)
def get_validation_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole([UserRole.ADMIN]))
):
    sessions = db.query(ValidationSession).all()
    responses = db.query(ValidationResponse).all()

    total_sessions = len(sessions)
    if total_sessions == 0:
        return ValidationSummaryResponse(
            total_participants=0,
            completed_sessions=0,
            average_overall_rating=0.0,
            average_rating_per_question=[],
            average_rating_by_role=[],
            completion_rate=0.0,
            comments=[],
            difficulty_areas=[]
        )

    # Completed session is one with at least one response submitted
    session_with_responses = db.query(ValidationResponse.session_id).distinct().all()
    completed_sessions_count = len(session_with_responses)

    avg_overall = db.query(func.avg(ValidationResponse.rating)).scalar() or 0.0

    # Question-wise ratings
    q_ratings_raw = db.query(
        ValidationResponse.question_id,
        func.avg(ValidationResponse.rating)
    ).group_by(ValidationResponse.question_id).all()
    
    question_ratings = [
        QuestionRating(question_id=row[0], average_rating=round(float(row[1]), 2))
        for row in q_ratings_raw
    ]

    # Role-wise ratings
    role_ratings_raw = db.query(
        ValidationSession.stakeholder_role,
        func.avg(ValidationResponse.rating)
    ).join(ValidationResponse, ValidationResponse.session_id == ValidationSession.id).group_by(ValidationSession.stakeholder_role).all()

    role_ratings = [
        RoleRating(role=row[0], average_rating=round(float(row[1]), 2))
        for row in role_ratings_raw
    ]

    # Comments collection
    comments_raw = db.query(
        ValidationSession.stakeholder_role,
        ValidationResponse.comment,
        ValidationResponse.question_id
    ).join(ValidationResponse, ValidationResponse.session_id == ValidationSession.id).filter(ValidationResponse.comment != None, ValidationResponse.comment != "").all()

    comments = [
        FeedbackComment(role=row[0], comment=row[1], question_id=row[2])
        for row in comments_raw
    ]

    # Difficulty areas (questions where avg rating <= 3.0)
    difficulty_areas = []
    for qr in question_ratings:
        if qr.average_rating <= 3.0:
            difficulty_areas.append(f"{qr.question_id} (Average Score: {qr.average_rating}/5.0)")

    return ValidationSummaryResponse(
        total_participants=total_sessions,
        completed_sessions=completed_sessions_count,
        average_overall_rating=round(float(avg_overall), 2),
        average_rating_per_question=question_ratings,
        average_rating_by_role=role_ratings,
        completion_rate=round(completed_sessions_count / total_sessions, 4),
        comments=comments,
        difficulty_areas=difficulty_areas
    )


@router.get("/admin/responses", response_model=List[ValidationResponseOut])
def get_validation_responses(
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole([UserRole.ADMIN]))
):
    return db.query(ValidationResponse).order_by(ValidationResponse.created_at.desc()).all()
