from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.database import Base

class UserRole(str, enum.Enum):
    RESTAURANT = "restaurant"
    RIDER = "rider"
    CUSTOMER = "customer"
    DISPATCHER = "dispatcher"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.RIDER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    deliveries_created = relationship("Delivery", back_populates="restaurant", foreign_keys="Delivery.restaurant_id")
    deliveries_assigned = relationship("Delivery", back_populates="rider", foreign_keys="Delivery.rider_id")
