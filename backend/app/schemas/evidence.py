from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.evidence import QualityClassification

class EvidenceSubmissionForm(BaseModel):
    delivery_id: str
    idempotency_key: str
    captured_latitude: Optional[float] = None
    captured_longitude: Optional[float] = None
    captured_timestamp: Optional[datetime] = None
    otp_entered: Optional[str] = None
    signature_base64: Optional[str] = None

class EvidenceResponse(BaseModel):
    id: str
    delivery_id: str
    rider_id: int
    photo_url: str
    signature_url: Optional[str]
    captured_latitude: Optional[float]
    captured_longitude: Optional[float]
    captured_timestamp: datetime
    is_offline_capture: bool
    otp_entered: Optional[str]
    otp_valid: bool
    distance_m: Optional[float]
    gps_valid: bool
    timestamp_valid: bool
    blur_score: Optional[float]
    brightness_score: Optional[float]
    photo_score: float
    gps_score: float
    timestamp_score: float
    signature_score: float
    otp_score: float
    total_quality_score: float
    classification: QualityClassification
    idempotency_key: str
    created_at: datetime

    class Config:
        from_attributes = True
