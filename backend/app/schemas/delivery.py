from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.delivery import DeliveryStatus

class DeliveryCreate(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "DEL-1003"})
    customer_name: str
    customer_phone: str
    delivery_address: str
    target_latitude: float
    target_longitude: float
    otp_code: str = Field(..., min_length=4, max_length=6)
    rider_id: Optional[int] = None
    customer_id: Optional[int] = None

class DeliveryStatusUpdate(BaseModel):
    status: DeliveryStatus
    reason_code: Optional[str] = "DISPATCHER_MANUAL_UPDATE"
    reason_text: Optional[str] = "Manual status override executed by dispatcher"

class DeliveryResponse(BaseModel):
    id: str
    order_id: Optional[str] = None
    restaurant_id: int
    rider_id: Optional[int]
    customer_id: Optional[int]
    customer_name: str
    customer_phone: str
    delivery_address: str
    target_latitude: float
    target_longitude: float
    otp_code: str
    status: DeliveryStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
