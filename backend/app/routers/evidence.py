import base64
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.delivery import Delivery, DeliveryStatus
from app.models.evidence import Evidence, QualityClassification
from app.schemas.evidence import EvidenceResponse
from app.dependencies import get_current_user, RequireRole
from app.services.storage import save_uploaded_file
from app.services.quality_engine import evaluate_evidence

router = APIRouter(prefix="/evidence", tags=["Evidence"])

@router.post("/submit", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def submit_evidence(
    delivery_id: str = Form(...),
    idempotency_key: str = Form(...),
    captured_latitude: Optional[float] = Form(None),
    captured_longitude: Optional[float] = Form(None),
    captured_timestamp: Optional[str] = Form(None),
    otp_entered: Optional[str] = Form(None),
    signature_base64: Optional[str] = Form(None),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole([UserRole.RIDER, UserRole.ADMIN]))
):
    # 1. Idempotency Check
    existing_evidence = db.query(Evidence).filter(Evidence.idempotency_key == idempotency_key).first()
    if existing_evidence:
        return existing_evidence

    # 2. Fetch Delivery Record
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    # 3. Read Photo File & Save
    photo_bytes = await photo.read()
    photo_url = save_uploaded_file(photo_bytes, filename_prefix=f"photo_{delivery_id}", extension=".jpg")

    # 4. Handle Signature File if present
    signature_url = None
    has_signature = False
    if signature_base64 and len(signature_base64.strip()) > 0:
        has_signature = True
        try:
            # Strip data URL prefix if present (e.g. data:image/png;base64,...)
            if "," in signature_base64:
                header, encoded = signature_base64.split(",", 1)
            else:
                encoded = signature_base64
            sig_bytes = base64.b64decode(encoded)
            signature_url = save_uploaded_file(sig_bytes, filename_prefix=f"sig_{delivery_id}", extension=".png")
        except Exception:
            has_signature = False

    # 5. Parse timestamp
    timestamp_dt = datetime.utcnow()
    if captured_timestamp:
        try:
            timestamp_dt = datetime.fromisoformat(captured_timestamp.replace("Z", "+00:00"))
        except Exception:
            timestamp_dt = datetime.utcnow()

    # 6. Run Evidence Quality Engine Evaluation
    eval_result = evaluate_evidence(
        image_bytes=photo_bytes,
        has_signature=has_signature,
        captured_latitude=captured_latitude,
        captured_longitude=captured_longitude,
        captured_timestamp=timestamp_dt,
        otp_entered=otp_entered,
        target_latitude=delivery.target_latitude,
        target_longitude=delivery.target_longitude,
        target_otp=delivery.otp_code
    )

    # 7. Create Evidence Record
    evidence = Evidence(
        id=str(uuid.uuid4()),
        delivery_id=delivery_id,
        rider_id=current_user.id,
        photo_url=photo_url,
        signature_url=signature_url,
        captured_latitude=captured_latitude,
        captured_longitude=captured_longitude,
        captured_timestamp=timestamp_dt,
        is_offline_capture=eval_result["is_offline_capture"],
        otp_entered=otp_entered,
        otp_valid=eval_result["otp_valid"],
        distance_m=eval_result["distance_m"],
        gps_valid=eval_result["gps_valid"],
        timestamp_valid=eval_result["timestamp_valid"],
        blur_score=eval_result["blur_score"],
        brightness_score=eval_result["brightness_score"],
        photo_score=eval_result["photo_score"],
        gps_score=eval_result["gps_score"],
        timestamp_score=eval_result["timestamp_score"],
        signature_score=eval_result["signature_score"],
        otp_score=eval_result["otp_score"],
        total_quality_score=eval_result["total_quality_score"],
        classification=eval_result["classification"],
        idempotency_key=idempotency_key
    )

    # 8. Update Delivery Status based on classification
    if eval_result["classification"] == QualityClassification.ACCEPTED:
        delivery.status = DeliveryStatus.DELIVERED
    elif eval_result["classification"] == QualityClassification.NEEDS_MANUAL_REVIEW:
        delivery.status = DeliveryStatus.NEEDS_REVIEW
    else:
        delivery.status = DeliveryStatus.DISPUTED

    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence

@router.get("/{delivery_id}", response_model=EvidenceResponse)
def get_evidence_by_delivery(
    delivery_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    evidence = db.query(Evidence).filter(Evidence.delivery_id == delivery_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="No evidence found for this delivery")
    return evidence
