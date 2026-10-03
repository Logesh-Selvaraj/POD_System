from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, event
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class AuditLog(Base):
    """
    Append-only immutable audit trail for every state-changing action in the
    POD system.

    WHY APPEND-ONLY:
        Delivery evidence and dispatcher overrides may be used in commercial
        disputes or legal proceedings.  If audit records could be silently
        updated or deleted an operator could retroactively alter the evidence
        trail, undermining its legal and regulatory value.

        Immutability is enforced at two complementary layers:
        1. SQLAlchemy event listeners (below) — prevent accidental mutations
           from the ORM layer in the Python application.
        2. PostgreSQL trigger in production — prevents direct SQL mutations
           that bypass the ORM entirely (see init_db.py / migration scripts).

    FIELDS:
        actor_id     — the authenticated user (dispatcher, rider, admin)
                       who caused the event; NULL for system-generated events.
        entity_type  — the type of record changed (e.g. "DELIVERY", "DISPUTE").
        entity_id    — the primary key of the changed record.
        action       — machine-readable event code
                       (e.g. "CREATE_DELIVERY", "dispatcher_override").
        previous_state / new_state — JSON snapshots of relevant field values
                       before and after the change.  Full-row snapshots are
                       intentionally avoided to reduce storage and to avoid
                       capturing sensitive PII.
        reason       — human-readable justification, mandatory for dispatcher
                       override events.
    """
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True)  # UUID string
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    entity_type = Column(String, nullable=False)  # e.g. "DELIVERY", "EVIDENCE", "DISPUTE"
    entity_id = Column(String, nullable=False)
    action = Column(String, nullable=False)  # e.g. "CREATE", "STATUS_OVERRIDE", "EVIDENCE_SUBMIT"

    previous_state = Column(Text, nullable=True)  # JSON representation
    new_state = Column(Text, nullable=True)        # JSON representation
    reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    actor = relationship("User")


# ── Append-only enforcement via SQLAlchemy session-level listeners ───────────
# These listeners fire BEFORE the ORM flushes the session to the database,
# giving them the opportunity to abort the operation with a PermissionError.
# The error propagates up the call stack and rolls back the transaction.
#
# NOTE: These listeners only protect the SQLAlchemy session layer.  In
# production PostgreSQL environments, a complementary database-level trigger
# (CREATE RULE / BEFORE UPDATE/DELETE) provides defence-in-depth against
# direct SQL access that bypasses the application.

@event.listens_for(AuditLog, "before_update")
def prevent_audit_log_update(mapper, connection, target):
    """Abort any ORM-initiated UPDATE on an audit_log row."""
    raise PermissionError("audit_logs is an append-only table and cannot be updated.")

@event.listens_for(AuditLog, "before_delete")
def prevent_audit_log_delete(mapper, connection, target):
    """Abort any ORM-initiated DELETE on an audit_log row."""
    raise PermissionError("audit_logs is an append-only table and cannot be deleted.")
