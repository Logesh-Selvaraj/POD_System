import uuid
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import asc, nullsfirst

from app.database import get_db
from app.models.user import User, UserRole
from app.models.delivery import Delivery, DeliveryStatus
from app.models.evidence import Evidence
from app.models.dispatcher_override import DispatcherOverride
from app.models.audit_log import AuditLog
from app.models.dispute import Dispute
from app.schemas.dispatcher import (
    DispatcherOverrideCreate,
    DispatcherOverrideResponse,
    DispatcherQueueItem,
    DisputeInfo,
    HistoryEventResponse
)
from app.schemas.delivery import DeliveryResponse
from app.schemas.evidence import EvidenceResponse
from app.dependencies import get_current_user, RequireRole

router = APIRouter(prefix="/dispatcher", tags=["Dispatcher"])

@router.get("/queue", response_model=List[DispatcherQueueItem])
def get_dispatcher_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole([UserRole.DISPATCHER, UserRole.ADMIN]))
):
    deliveries = (
        db.query(Delivery)
        .outerjoin(Evidence, Evidence.delivery_id == Delivery.id)
        .filter(Delivery.status.in_([DeliveryStatus.NEEDS_REVIEW, DeliveryStatus.DISPUTED]))
        .order_by(
            nullsfirst(asc(Evidence.total_quality_score)),
            asc(Delivery.created_at)
        )
        .all()
    )

    result = []
    for d in deliveries:
        ev = db.query(Evidence).filter(Evidence.delivery_id == d.id).first()
        disputes = db.query(Dispute).filter(Dispute.delivery_id == d.id).all()
        
        rider = db.query(User).filter(User.id == d.rider_id).first() if d.rider_id else None
        restaurant = db.query(User).filter(User.id == d.restaurant_id).first() if d.restaurant_id else None

        result.append(
            DispatcherQueueItem(
                delivery=DeliveryResponse.model_validate(d),
                evidence=EvidenceResponse.model_validate(ev) if ev else None,
                disputes=[DisputeInfo.model_validate(disp) for disp in disputes],
                rider_name=rider.full_name if rider else None,
                restaurant_name=restaurant.full_name if restaurant else None
            )
        )
    return result

@router.post("/overrides", response_model=DispatcherOverrideResponse, status_code=status.HTTP_201_CREATED)
def create_dispatcher_override(
    override_in: DispatcherOverrideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole([UserRole.DISPATCHER, UserRole.ADMIN]))
):
    # 1. Fetch Delivery
    delivery = db.query(Delivery).filter(Delivery.id == override_in.delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail=f"Delivery {override_in.delivery_id} not found")

    previous_status = delivery.status.value
    new_status_str = override_in.new_status.value
    reason_code_str = override_in.reason_code.value
    reason_text_str = override_in.reason_text or ""

    # Status Transition Validation
    # We must explicitly define and document allowed transitions.
    # Typical dispatcher override transitions allow changing from NEEDS_REVIEW or DISPUTED to DELIVERED, NEEDS_REVIEW, DISPUTED, ASSIGNED, etc.
    # Let's allow overriding status if previous_status is NEEDS_REVIEW, DISPUTED, or if it's already DELIVERED (e.g. going back to NEEDS_REVIEW).
    # Since we can transition to any valid status as long as we are dispatcher/admin, let's allow:
    # NEEDS_REVIEW -> any
    # DISPUTED -> any
    # DELIVERED -> NEEDS_REVIEW or DISPUTED (for re-evaluation)
    # IN_TRANSIT -> any (in case they need to intervene)
    # Let's check if the transition is allowed.
    allowed_from_statuses = [DeliveryStatus.NEEDS_REVIEW.value, DeliveryStatus.DISPUTED.value, DeliveryStatus.DELIVERED.value, DeliveryStatus.IN_TRANSIT.value, DeliveryStatus.ASSIGNED.value, DeliveryStatus.PENDING.value]
    if previous_status not in allowed_from_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot override delivery in status '{previous_status}'"
        )

    # 2. Update Delivery status
    delivery.status = override_in.new_status
    delivery.updated_at = datetime.utcnow()

    # 3. Create DispatcherOverride record
    override_record = DispatcherOverride(
        id=str(uuid.uuid4()),
        delivery_id=delivery.id,
        dispatcher_id=current_user.id,  # Identity from JWT
        previous_status=previous_status,
        new_status=new_status_str,
        reason_code=reason_code_str,
        reason_text=reason_text_str,
        created_at=datetime.utcnow()
    )
    db.add(override_record)

    # 4. Create AuditLog record
    audit_reason = f"{reason_code_str}: {reason_text_str}" if reason_text_str else reason_code_str
    audit_record = AuditLog(
        id=str(uuid.uuid4()),
        actor_id=current_user.id,
        entity_type="delivery",
        entity_id=delivery.id,
        action="dispatcher_override",
        previous_state=json.dumps({"status": previous_status, "delivery_id": delivery.id}),
        new_state=json.dumps({
            "status": new_status_str,
            "reason_code": reason_code_str,
            "reason_text": reason_text_str,
            "dispatcher_id": current_user.id
        }),
        reason=audit_reason,
        created_at=datetime.utcnow()
    )
    db.add(audit_record)

    db.commit()
    db.refresh(override_record)
    return override_record

@router.get("/deliveries/{delivery_id}/history", response_model=List[HistoryEventResponse])
def get_delivery_history(
    delivery_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole([UserRole.DISPATCHER, UserRole.ADMIN]))
):
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail=f"Delivery {delivery_id} not found")

    events: List[HistoryEventResponse] = []

    # 1. Fetch Overrides
    overrides = db.query(DispatcherOverride).filter(DispatcherOverride.delivery_id == delivery_id).all()
    for ov in overrides:
        dispatcher_user = db.query(User).filter(User.id == ov.dispatcher_id).first()
        events.append(
            HistoryEventResponse(
                id=ov.id,
                event_type="OVERRIDE",
                timestamp=ov.created_at,
                actor_id=ov.dispatcher_id,
                actor_name=dispatcher_user.full_name if dispatcher_user else f"User #{ov.dispatcher_id}",
                action_or_reason_code=ov.reason_code,
                previous_status=ov.previous_status,
                new_status=ov.new_status,
                reason_text=ov.reason_text,
                details={"dispatcher_id": ov.dispatcher_id}
            )
        )

    # 2. Fetch Audit Logs
    audit_logs = db.query(AuditLog).filter(
        AuditLog.entity_id == delivery_id
    ).all()
    for al in audit_logs:
        actor_user = db.query(User).filter(User.id == al.actor_id).first() if al.actor_id else None
        prev_st = None
        new_st = None
        if al.previous_state:
            try:
                prev_st = json.loads(al.previous_state).get("status")
            except Exception:
                pass
        if al.new_state:
            try:
                new_st = json.loads(al.new_state).get("status")
            except Exception:
                pass

        events.append(
            HistoryEventResponse(
                id=al.id,
                event_type="AUDIT",
                timestamp=al.created_at,
                actor_id=al.actor_id,
                actor_name=actor_user.full_name if actor_user else (f"User #{al.actor_id}" if al.actor_id else "System"),
                action_or_reason_code=al.action,
                previous_status=prev_st,
                new_status=new_st,
                reason_text=al.reason,
                details={"action": al.action}
            )
        )

    # 3. Fetch Disputes
    disputes = db.query(Dispute).filter(Dispute.delivery_id == delivery_id).all()
    for disp in disputes:
        disputer = db.query(User).filter(User.id == disp.raised_by_user_id).first()
        events.append(
            HistoryEventResponse(
                id=disp.id,
                event_type="DISPUTE",
                timestamp=disp.created_at,
                actor_id=disp.raised_by_user_id,
                actor_name=disputer.full_name if disputer else f"User #{disp.raised_by_user_id}",
                action_or_reason_code="DISPUTE_RAISED",
                previous_status=None,
                new_status=disp.status,
                reason_text=disp.reason,
                details={"status": disp.status, "resolution": disp.resolution_notes}
            )
        )

    # Sort events by timestamp ASC
    events.sort(key=lambda x: x.timestamp)
    return events
