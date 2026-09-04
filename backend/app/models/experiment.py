from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    dataset_size = Column(Integer, default=0)
    baseline_description = Column(String, nullable=True)
    proposed_system_description = Column(String, nullable=True)

    results = relationship("ExperimentResult", back_populates="run", cascade="all, delete-orphan")


class ExperimentCase(Base):
    __tablename__ = "experiment_cases"

    case_id = Column(String, primary_key=True, index=True)
    scenario_type = Column(String, nullable=False)
    photo_quality = Column(String, nullable=False)  # "blur", "good", "none"
    gps_available = Column(Boolean, default=True)
    gps_distance_meters = Column(Float, nullable=True)
    timestamp_valid = Column(Boolean, default=True)
    signature_available = Column(Boolean, default=True)
    otp_valid = Column(Boolean, default=True)
    network_available = Column(Boolean, default=True)
    expected_delivery_outcome = Column(String, nullable=False)  # "ACCEPTED", "NEEDS_MANUAL_REVIEW", "DISPUTE"
    notes = Column(String, nullable=True)

    results = relationship("ExperimentResult", back_populates="case", cascade="all, delete-orphan")


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    result_id = Column(String, primary_key=True, index=True)
    experiment_run_id = Column(String, ForeignKey("experiment_runs.id"), nullable=False)
    case_id = Column(String, ForeignKey("experiment_cases.case_id"), nullable=False)
    system_type = Column(String, nullable=False)  # "BASELINE", "PROPOSED"
    evidence_complete = Column(Boolean, default=False)
    evidence_valid = Column(Boolean, default=False)
    dispute_created = Column(Boolean, default=False)
    dispute_resolved = Column(Boolean, default=False)
    false_positive = Column(Boolean, default=False)
    false_negative = Column(Boolean, default=False)
    processing_time_ms = Column(Float, default=0.0)
    final_classification = Column(String, nullable=False)
    notes = Column(String, nullable=True)

    run = relationship("ExperimentRun", back_populates="results")
    case = relationship("ExperimentCase", back_populates="results")
