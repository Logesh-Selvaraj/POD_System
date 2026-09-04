from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, event
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True) # UUID string
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    entity_type = Column(String, nullable=False) # e.g. "DELIVERY", "EVIDENCE", "DISPUTE"
    entity_id = Column(String, nullable=False)
    action = Column(String, nullable=False) # e.g. "CREATE", "STATUS_OVERRIDE", "EVIDENCE_SUBMIT"
    
    previous_state = Column(Text, nullable=True) # JSON representation
    new_state = Column(Text, nullable=True)      # JSON representation
    reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    actor = relationship("User")

# Append-only enforcement via SQLAlchemy listeners
@event.listens_for(AuditLog, "before_update")
def prevent_audit_log_update(mapper, connection, target):
    raise PermissionError("audit_logs is an append-only table and cannot be updated.")

@event.listens_for(AuditLog, "before_delete")
def prevent_audit_log_delete(mapper, connection, target):
    raise PermissionError("audit_logs is an append-only table and cannot be deleted.")
