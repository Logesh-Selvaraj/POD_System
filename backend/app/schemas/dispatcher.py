import enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator

from app.models.delivery import DeliveryStatus
from app.schemas.delivery import DeliveryResponse
from app.schemas.evidence import EvidenceResponse

class OverrideReasonCode(str, enum.Enum):
    CUSTOMER_CONFIRMED_RECEIPT = "CUSTOMER_CONFIRMED_RECEIPT"
    GPS_UNAVAILABLE = "GPS_UNAVAILABLE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    SIGNATURE_UNAVAILABLE = "SIGNATURE_UNAVAILABLE"
    EVIDENCE_EXCEPTION = "EVIDENCE_EXCEPTION"
    OPERATIONAL_EXCEPTION = "OPERATIONAL_EXCEPTION"
    OTHER = "OTHER"

class DispatcherOverrideCreate(BaseModel):
    delivery_id: str
    new_status: DeliveryStatus
    reason_code: OverrideReasonCode
    reason_text: Optional[str] = None

    @model_validator(mode="after")
    def validate_reason_text(self):
        if self.reason_code == OverrideReasonCode.OTHER:
            if not self.reason_text or len(self.reason_text.strip()) < 10:
                raise ValueError("Reason text must be at least 10 characters when reason code is OTHER")
        return self

class DispatcherOverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    delivery_id: str
    dispatcher_id: int
    previous_status: str
    new_status: str
    reason_code: str
    reason_text: str
    created_at: datetime

class DisputeInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    delivery_id: str
    raised_by_user_id: int
    reason: str
    status: str
    resolution_notes: Optional[str] = None
    created_at: datetime

class DispatcherQueueItem(BaseModel):
    delivery: DeliveryResponse
    evidence: Optional[EvidenceResponse] = None
    disputes: List[DisputeInfo] = []
    rider_name: Optional[str] = None
    restaurant_name: Optional[str] = None

class HistoryEventResponse(BaseModel):
    id: str
    event_type: str  # "OVERRIDE", "AUDIT", "DISPUTE"
    timestamp: datetime
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    action_or_reason_code: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    reason_text: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
