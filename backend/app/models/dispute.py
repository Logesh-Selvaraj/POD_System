from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(String, primary_key=True, index=True) # UUID string
    delivery_id = Column(String, ForeignKey("deliveries.id"), nullable=False)
    raised_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    reason = Column(String, nullable=False)
    status = Column(String, default="OPEN", nullable=False) # OPEN, RESOLVED_REFUNDED, RESOLVED_REJECTED
    resolution_notes = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    delivery = relationship("Delivery", back_populates="disputes")
    raised_by = relationship("User")
