from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from datetime import datetime

from app.database import Base

class SyncQueueItem(Base):
    __tablename__ = "sync_queue"

    id = Column(String, primary_key=True, index=True) # UUID string
    idempotency_key = Column(String, unique=True, index=True, nullable=False)
    delivery_id = Column(String, ForeignKey("deliveries.id"), nullable=False)
    status = Column(String, default="PENDING") # PENDING, PROCESSED, FAILED
    payload = Column(Text, nullable=False) # JSON encoded offline payload
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
