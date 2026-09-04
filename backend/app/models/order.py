from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True) # e.g. ORD-1001
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    items_summary = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    
    target_address = Column(String, nullable=False)
    target_latitude = Column(Float, nullable=False)
    target_longitude = Column(Float, nullable=False)
    
    otp_code = Column(String(6), nullable=False)
    status = Column(String, default="PENDING", nullable=False) # PENDING, ASSIGNED, COMPLETED, DISPUTED
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    deliveries = relationship("Delivery", back_populates="order")
