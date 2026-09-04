from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.database import Base

class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    NEEDS_REVIEW = "needs_review"
    DISPUTED = "disputed"

class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(String, primary_key=True, index=True) # e.g. DEL-1001
    order_id = Column(String, ForeignKey("orders.id"), nullable=True) # Link to Order table
    rider_profile_id = Column(Integer, ForeignKey("riders.id"), nullable=True) # Link to Rider table
    
    restaurant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rider_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    delivery_address = Column(String, nullable=False)
    
    # Target Coordinates
    target_latitude = Column(Float, nullable=False)
    target_longitude = Column(Float, nullable=False)
    
    otp_code = Column(String(6), nullable=False)
    status = Column(SQLEnum(DeliveryStatus), default=DeliveryStatus.PENDING, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="deliveries")
    rider_profile = relationship("Rider", back_populates="deliveries")
    restaurant = relationship("User", foreign_keys=[restaurant_id], back_populates="deliveries_created")
    rider = relationship("User", foreign_keys=[rider_id], back_populates="deliveries_assigned")
    evidence = relationship("Evidence", back_populates="delivery", uselist=False)
    disputes = relationship("Dispute", back_populates="delivery")
    overrides = relationship("DispatcherOverride", back_populates="delivery")
