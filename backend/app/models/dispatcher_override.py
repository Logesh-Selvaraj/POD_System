from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class DispatcherOverride(Base):
    __tablename__ = "dispatcher_overrides"

    id = Column(String, primary_key=True, index=True) # UUID string
    delivery_id = Column(String, ForeignKey("deliveries.id"), nullable=False)
    dispatcher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    previous_status = Column(String, nullable=False)
    new_status = Column(String, nullable=False)
    reason_code = Column(String, nullable=False) # e.g. "CUSTOMER_VERIFIED_OFFLINE", "BLURRY_PHOTO_VALIDATED"
    reason_text = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    delivery = relationship("Delivery", back_populates="overrides")
    dispatcher = relationship("User")
