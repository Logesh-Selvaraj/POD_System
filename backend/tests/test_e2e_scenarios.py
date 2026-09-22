import os
os.environ["USE_SQLITE"] = "true"
import base64
import uuid
import pytest
import numpy as np
import cv2
from datetime import datetime

from fastapi.testclient import TestClient
from app.main import app
from app.init_db import init_db, SessionLocal
from app.models import (
    Delivery, DeliveryStatus,
    Evidence, QualityClassification,
    AuditLog, DispatcherOverride
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db(reset=True)

def get_rider_token() -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "rider@pod.com", "password": "rider123"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]

def get_dispatcher_token() -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "dispatcher@pod.com", "password": "dispatcher123"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]

def generate_synthetic_image(blur: bool = False) -> bytes:
    """
    Generates a synthetic image. If blur is True, applies Gaussian blur
    so Laplacian variance drops well below the 100.0 threshold.
    """
    img = np.full((300, 300, 3), 128, dtype=np.uint8)
    cv2.putText(img, "POD DELIVERY PROOF", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.rectangle(img, (30, 30), (270, 270), (0, 255, 0), 3)
    if blur:
        img = cv2.GaussianBlur(img, (25, 25), 0)
    _, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes()

def get_sample_signature_b64() -> str:
    sig_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    return "data:image/png;base64," + base64.b64encode(sig_bytes).decode("utf-8")


# ==============================================================================
# 1. E2E Test: GPS Missing Scenario
# ==============================================================================
def test_e2e_gps_missing_routes_to_needs_review():
    """
    End-to-End API test: Rider delivers order DEL-1001 with clear photo, valid signature,
    and valid OTP, but GPS coordinates are unavailable (None / omitted).
    Expected Outcome:
    - Evidence accepted with gps_score = 0.0, is_offline_capture = True
    - Total quality score = 75.0 (Photo 25 + Time 20 + Sig 20 + OTP 10)
    - Quality classification = NEEDS_MANUAL_REVIEW
    - Delivery status transitions from ASSIGNED to NEEDS_REVIEW
    """
    rider_token = get_rider_token()
    photo_bytes = generate_synthetic_image(blur=False)
    sig_b64 = get_sample_signature_b64()
    idempotency_key = f"E2E-GPS-MISSING-{uuid.uuid4()}"

    # Submit evidence with missing GPS coordinates
    form_data = {
        "delivery_id": "DEL-1001",
        "idempotency_key": idempotency_key,
        "captured_timestamp": datetime.utcnow().isoformat(),
        "otp_entered": "4829",
        "signature_base64": sig_b64
    }
    files = {
        "photo": ("proof.jpg", photo_bytes, "image/jpeg")
    }

    response = client.post(
        "/api/v1/evidence/submit",
        data=form_data,
        files=files,
        headers={"Authorization": f"Bearer {rider_token}"}
    )
    assert response.status_code == 201
    evidence = response.json()

    # Assert evidence evaluation metrics
    assert evidence["delivery_id"] == "DEL-1001"
    assert evidence["gps_valid"] is False
    assert evidence["gps_score"] == 0.0
    assert evidence["is_offline_capture"] is True
    assert evidence["photo_score"] == 25.0
    assert evidence["signature_score"] == 20.0
    assert evidence["otp_score"] == 10.0
    assert evidence["timestamp_score"] == 20.0
    assert evidence["total_quality_score"] == 75.0
    assert evidence["classification"] == "NEEDS_MANUAL_REVIEW"

    # Assert delivery record status updated to needs_review
    del_resp = client.get(
        "/api/v1/deliveries/DEL-1001",
        headers={"Authorization": f"Bearer {rider_token}"}
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "needs_review"


# ==============================================================================
# 2. E2E Test: Blurred Photo Scenarios
# ==============================================================================
def test_e2e_blurred_photo_routes_to_needs_review():
    """
    End-to-End API test: Rider submits evidence with a blurred photo.
    All other parameters (GPS, signature, timestamp, OTP) are valid.
    Expected Outcome:
    - Laplacian variance < OPENCV_BLUR_THRESHOLD (100.0)
    - Photo score reduced to 12.5
    - Total quality score = 87.5 (Photo 12.5 + GPS 25 + Time 20 + Sig 20 + OTP 10)
    - Quality classification = NEEDS_MANUAL_REVIEW
    - Delivery status transitions from IN_TRANSIT to NEEDS_REVIEW
    """
    rider_token = get_rider_token()
    blurred_photo = generate_synthetic_image(blur=True)
    sig_b64 = get_sample_signature_b64()
    idempotency_key = f"E2E-BLUR-REVIEW-{uuid.uuid4()}"

    form_data = {
        "delivery_id": "DEL-1002",
        "idempotency_key": idempotency_key,
        "captured_latitude": 12.935242,
        "captured_longitude": 77.624462,
        "captured_timestamp": datetime.utcnow().isoformat(),
        "otp_entered": "1593",
        "signature_base64": sig_b64
    }
    files = {
        "photo": ("blurry_proof.jpg", blurred_photo, "image/jpeg")
    }

    response = client.post(
        "/api/v1/evidence/submit",
        data=form_data,
        files=files,
        headers={"Authorization": f"Bearer {rider_token}"}
    )
    assert response.status_code == 201
    evidence = response.json()

    assert evidence["blur_score"] < 100.0
    assert evidence["photo_score"] == 12.5
    assert evidence["gps_score"] == 25.0
    assert evidence["total_quality_score"] == 87.5
    assert evidence["classification"] == "NEEDS_MANUAL_REVIEW"

    # Verify delivery status is updated to needs_review
    del_resp = client.get(
        "/api/v1/deliveries/DEL-1002",
        headers={"Authorization": f"Bearer {rider_token}"}
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "needs_review"


def test_e2e_blurred_photo_with_mismatch_routes_to_dispute():
    """
    End-to-End API test: Compound failure with blurred photo + incorrect OTP or distance mismatch.
    Expected Outcome:
    - Score falls below 70.0 threshold
    - Quality classification = DISPUTE
    - Delivery status transitions to DISPUTED
    """
    rider_token = get_rider_token()
    blurred_photo = generate_synthetic_image(blur=True)
    idempotency_key = f"E2E-BLUR-DISPUTE-{uuid.uuid4()}"

    # Target is (12.971598, 77.594566), captured is far away (13.05, 77.65) and wrong OTP
    form_data = {
        "delivery_id": "DEL-1001",
        "idempotency_key": idempotency_key,
        "captured_latitude": 13.050000,
        "captured_longitude": 77.650000,
        "captured_timestamp": datetime.utcnow().isoformat(),
        "otp_entered": "0000",
        "signature_base64": ""
    }
    files = {
        "photo": ("blurry_proof.jpg", blurred_photo, "image/jpeg")
    }

    response = client.post(
        "/api/v1/evidence/submit",
        data=form_data,
        files=files,
        headers={"Authorization": f"Bearer {rider_token}"}
    )
    assert response.status_code == 201
    evidence = response.json()

    assert evidence["total_quality_score"] < 70.0
    assert evidence["classification"] == "DISPUTE"

    # Verify delivery status is disputed
    del_resp = client.get(
        "/api/v1/deliveries/DEL-1001",
        headers={"Authorization": f"Bearer {rider_token}"}
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "disputed"


# ==============================================================================
# 3. E2E Test: Offline Scenario & Sync Idempotency
# ==============================================================================
def test_e2e_offline_scenario_idempotency_and_dispatcher_override():
    """
    End-to-End API test:
    1. Courier captures evidence offline (no GPS, flagged as offline capture).
    2. Courier syncs evidence upon reconnection.
    3. Duplicate sync attempt with identical idempotency_key is returned safely without duplicates.
    4. Dispatcher inspects the review queue and performs an approved override with audit logging.
    5. Final delivery status transitions to DELIVERED.
    """
    rider_token = get_rider_token()
    dispatcher_token = get_dispatcher_token()
    photo_bytes = generate_synthetic_image(blur=False)
    sig_b64 = get_sample_signature_b64()
    idempotency_key = f"OFFLINE-PWA-SYNC-{uuid.uuid4()}"

    # Step 1: Initial offline sync
    form_data = {
        "delivery_id": "DEL-1001",
        "idempotency_key": idempotency_key,
        "captured_timestamp": datetime.utcnow().isoformat(),
        "otp_entered": "4829",
        "signature_base64": sig_b64
    }
    files = {
        "photo": ("offline_proof.jpg", photo_bytes, "image/jpeg")
    }

    resp1 = client.post(
        "/api/v1/evidence/submit",
        data=form_data,
        files=files,
        headers={"Authorization": f"Bearer {rider_token}"}
    )
    assert resp1.status_code == 201
    ev1 = resp1.json()
    assert ev1["is_offline_capture"] is True
    assert ev1["classification"] == "NEEDS_MANUAL_REVIEW"

    # Step 2: Idempotent resubmission (network blip retry)
    resp2 = client.post(
        "/api/v1/evidence/submit",
        data=form_data,
        files={"photo": ("offline_proof.jpg", photo_bytes, "image/jpeg")},
        headers={"Authorization": f"Bearer {rider_token}"}
    )
    assert resp2.status_code in [200, 201]
    ev2 = resp2.json()
    assert ev2["id"] == ev1["id"]

    # Step 3: Dispatcher checks the review queue
    queue_resp = client.get(
        "/api/v1/dispatcher/queue",
        headers={"Authorization": f"Bearer {dispatcher_token}"}
    )
    assert queue_resp.status_code == 200
    queue_deliveries = queue_resp.json()
    assert any(d["delivery"]["id"] == "DEL-1001" for d in queue_deliveries)

    # Step 4: Dispatcher performs an authorized override
    override_payload = {
        "delivery_id": "DEL-1001",
        "new_status": "delivered",
        "reason_code": "NETWORK_FAILURE",
        "reason_text": "Verified offline recipient signature and valid OTP match during delivery."
    }
    override_resp = client.post(
        "/api/v1/dispatcher/overrides",
        json=override_payload,
        headers={"Authorization": f"Bearer {dispatcher_token}"}
    )
    assert override_resp.status_code == 201

    # Step 5: Assert final outcomes
    # Delivery status must now be DELIVERED
    del_final = client.get(
        "/api/v1/deliveries/DEL-1001",
        headers={"Authorization": f"Bearer {rider_token}"}
    )
    assert del_final.status_code == 200
    assert del_final.json()["status"] == "delivered"

    # Verify audit log was committed
    db = SessionLocal()
    try:
        audit_entry = db.query(AuditLog).filter(
            AuditLog.entity_id == "DEL-1001",
            AuditLog.action == "dispatcher_override"
        ).first()
        assert audit_entry is not None
        assert "delivered" in audit_entry.new_state
    finally:
        db.close()
