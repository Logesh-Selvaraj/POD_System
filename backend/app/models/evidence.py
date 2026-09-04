from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.database import Base

class QualityClassification(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"
    DISPUTE = "DISPUTE"

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, index=True) # UUID string
    delivery_id = Column(String, ForeignKey("deliveries.id"), unique=True, nullable=False)
    rider_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    photo_url = Column(String, nullable=False)
    signature_url = Column(String, nullable=True)
    
    captured_latitude = Column(Float, nullable=True)
    captured_longitude = Column(Float, nullable=True)
    captured_timestamp = Column(DateTime, nullable=False)
    is_offline_capture = Column(Boolean, default=False)
    
    otp_entered = Column(String(6), nullable=True)
    otp_valid = Column(Boolean, default=False)
    
    # Engine Calculations
    distance_m = Column(Float, nullable=True)
    gps_valid = Column(Boolean, default=False)
    timestamp_valid = Column(Boolean, default=False)
    
    blur_score = Column(Float, nullable=True) # Laplacian variance
    brightness_score = Column(Float, nullable=True) # Mean brightness
    
    # Granular Scores
    photo_score = Column(Float, default=0.0)      # max 25
    gps_score = Column(Float, default=0.0)        # max 25
    timestamp_score = Column(Float, default=0.0)  # max 20
    signature_score = Column(Float, default=0.0)  # max 20
    otp_score = Column(Float, default=0.0)        # max 10
    
    total_quality_score = Column(Float, default=0.0) # 0 to 100
    classification = Column(SQLEnum(QualityClassification), nullable=False)
    
    idempotency_key = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    delivery = relationship("Delivery", back_populates="evidence")
    rider = relationship("User")
