import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.user import User, UserRole
from app.models.delivery import Delivery, DeliveryStatus
from app.models.dispatcher_override import DispatcherOverride
from app.models.audit_log import AuditLog
from app.schemas.delivery import DeliveryCreate, DeliveryResponse, DeliveryStatusUpdate
from app.dependencies import get_current_user, RequireRole

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])

@router.post("/", response_model=DeliveryResponse, status_code=status.HTTP_201_CREATED)
def create_delivery(
    delivery_in: DeliveryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole([UserRole.RESTAURANT, UserRole.ADMIN]))
):
    existing = db.query(Delivery).filter(Delivery.id == delivery_in.id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Delivery with ID {delivery_in.id} already exists")

    delivery = Delivery(
        id=delivery_in.id,
        restaurant_id=current_user.id if current_user.role == UserRole.RESTAURANT else (delivery_in.rider_id or current_user.id),
        rider_id=delivery_in.rider_id,
        customer_id=delivery_in.customer_id,
        customer_name=delivery_in.customer_name,
        customer_phone=delivery_in.customer_phone,
        delivery_address=delivery_in.delivery_address,
        target_latitude=delivery_in.target_latitude,
        target_longitude=delivery_in.target_longitude,
        otp_code=delivery_in.otp_code,
        status=DeliveryStatus.ASSIGNED if delivery_in.rider_id else DeliveryStatus.PENDING
    )
    db.add(delivery)
    db.commit()

    # Create Audit Log for creation
    audit = AuditLog(
        id=str(uuid.uuid4()),
        actor_id=current_user.id,
        entity_type="DELIVERY",
        entity_id=delivery.id,
        action="CREATE_DELIVERY",
        previous_state=None,
        new_state=json.dumps({"status": delivery.status.value, "customer_name": delivery.customer_name}),
        reason="Delivery initialized"
    )
    db.add(audit)
    db.commit()
    db.refresh(delivery)
    return delivery

@router.get("/", response_model=List[DeliveryResponse])
def list_deliveries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Delivery)
    if current_user.role == UserRole.RIDER:
        query = query.filter(Delivery.rider_id == current_user.id)
    elif current_user.role == UserRole.RESTAURANT:
        query = query.filter(Delivery.restaurant_id == current_user.id)
    elif current_user.role == UserRole.CUSTOMER:
        query = query.filter(Delivery.customer_id == current_user.id)
    
    return query.order_by(Delivery.created_at.desc()).all()

@router.get("/assigned", response_model=List[DeliveryResponse])
def get_assigned_deliveries(
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole([UserRole.RIDER, UserRole.ADMIN]))
):
    deliveries = db.query(Delivery).filter(
        Delivery.rider_id == current_user.id,
        Delivery.status.in_([DeliveryStatus.ASSIGNED, DeliveryStatus.IN_TRANSIT])
    ).all()
    return deliveries

@router.get("/{delivery_id}", response_model=DeliveryResponse)
def get_delivery_by_id(
    delivery_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return delivery

@router.patch("/{delivery_id}/status", response_model=DeliveryResponse)
def update_delivery_status(
    delivery_id: str,
    status_update: DeliveryStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    previous_status = delivery.status.value
    delivery.status = status_update.status

    # Record Dispatcher Override if user is dispatcher or admin
    if current_user.role in [UserRole.DISPATCHER, UserRole.ADMIN]:
        override_record = DispatcherOverride(
            id=str(uuid.uuid4()),
            delivery_id=delivery.id,
            dispatcher_id=current_user.id,
            previous_status=previous_status,
            new_status=status_update.status.value,
            reason_code=status_update.reason_code or "MANUAL_DISPATCHER_OVERRIDE",
            reason_text=status_update.reason_text or "Status updated via dispatcher dashboard"
        )
        db.add(override_record)

    # Record Audit Log
    audit = AuditLog(
        id=str(uuid.uuid4()),
        actor_id=current_user.id,
        entity_type="DELIVERY",
        entity_id=delivery.id,
        action="UPDATE_STATUS",
        previous_state=json.dumps({"status": previous_status}),
        new_state=json.dumps({"status": status_update.status.value}),
        reason=status_update.reason_text
    )
    db.add(audit)

    db.commit()
    db.refresh(delivery)
    return delivery

@router.delete("/{delivery_id}", status_code=status.HTTP_200_OK)
def delete_delivery(
    delivery_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    # Check permissions: Restaurant can delete their own delivery; Admin/Dispatcher can also delete
    if current_user.role == UserRole.RESTAURANT and delivery.restaurant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this delivery")
    
    from app.models.evidence import Evidence
    from app.models.dispute import Dispute
    from app.models.dispatcher_override import DispatcherOverride
    from app.models.sync_queue import SyncQueueItem

    db.query(Evidence).filter(Evidence.delivery_id == delivery_id).delete()
    db.query(Dispute).filter(Dispute.delivery_id == delivery_id).delete()
    db.query(DispatcherOverride).filter(DispatcherOverride.delivery_id == delivery_id).delete()
    db.query(SyncQueueItem).filter(SyncQueueItem.delivery_id == delivery_id).delete()

    del_id = delivery.id
    del_name = delivery.customer_name

    db.delete(delivery)
    db.commit()

    # Record Audit Log
    try:
        audit = AuditLog(
            id=str(uuid.uuid4()),
            actor_id=current_user.id,
            entity_type="DELIVERY",
            entity_id=del_id,
            action="DELETE_DELIVERY",
            previous_state=json.dumps({"id": del_id, "customer_name": del_name}),
            new_state=None,
            reason="Delivery deleted by user"
        )
        db.add(audit)
        db.commit()
    except Exception:
        pass

    return {"message": f"Delivery {del_id} deleted successfully", "id": del_id}
