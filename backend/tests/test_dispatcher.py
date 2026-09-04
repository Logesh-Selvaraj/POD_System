import pytest
import os
os.environ["USE_SQLITE"] = "true"

from fastapi.testclient import TestClient
from app.main import app
from app.init_db import init_db, SessionLocal
from app.models.delivery import Delivery, DeliveryStatus
from app.models.dispatcher_override import DispatcherOverride
from app.models.audit_log import AuditLog

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db(reset=True)

def get_token(email: str, password: str):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]

def get_dispatcher_token():
    return get_token("dispatcher@pod.com", "dispatcher123")

def get_admin_token():
    return get_token("dispatcher@pod.com", "dispatcher123") # Admin/Dispatcher account

def get_rider_token():
    return get_token("rider@pod.com", "rider123")

def get_customer_token():
    return get_token("customer@pod.com", "customer123")

# Test 1: Dispatcher can access queue
def test_dispatcher_can_access_queue():
    token = get_dispatcher_token()
    response = client.get(
        "/api/v1/dispatcher/queue",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    queue = response.json()
    assert isinstance(queue, list)
    # Check that items in queue are in NEEDS_REVIEW or DISPUTED
    for item in queue:
        assert item["delivery"]["status"] in ["needs_review", "disputed"]

# Test 2: Rider/customer cannot access dispatcher queue
def test_rider_customer_cannot_access_queue():
    rider_token = get_rider_token()
    resp_rider = client.get(
        "/api/v1/dispatcher/queue",
        headers={"Authorization": f"Bearer {rider_token}"}
    )
    assert resp_rider.status_code == 403

    customer_token = get_customer_token()
    resp_cust = client.get(
        "/api/v1/dispatcher/queue",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert resp_cust.status_code == 403

# Test 3: Valid dispatcher override succeeds
def test_valid_dispatcher_override_succeeds():
    token = get_dispatcher_token()
    payload = {
        "delivery_id": "DEL-1002",
        "new_status": "delivered",
        "reason_code": "CUSTOMER_CONFIRMED_RECEIPT",
        "reason_text": "Customer confirmed order receipt via phone call."
    }
    response = client.post(
        "/api/v1/dispatcher/overrides",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["delivery_id"] == "DEL-1002"
    assert data["previous_status"] in ["in_transit", "disputed", "needs_review"]
    assert data["new_status"] == "delivered"
    assert data["reason_code"] == "CUSTOMER_CONFIRMED_RECEIPT"

    # Verify delivery status updated
    del_resp = client.get(
        "/api/v1/deliveries/DEL-1002",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert del_resp.json()["status"] == "delivered"

# Test 4: Override without valid reason fails with 422
def test_override_without_valid_reason_fails_422():
    token = get_dispatcher_token()
    
    # Reason code OTHER requires reason_text >= 10 chars
    payload_invalid_text = {
        "delivery_id": "DEL-1002",
        "new_status": "delivered",
        "reason_code": "OTHER",
        "reason_text": "Short" # < 10 chars
    }
    response = client.post(
        "/api/v1/dispatcher/overrides",
        json=payload_invalid_text,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422

    # Invalid reason code string
    payload_invalid_code = {
        "delivery_id": "DEL-1002",
        "new_status": "delivered",
        "reason_code": "INVALID_CODE",
        "reason_text": "Valid text length here"
    }
    response2 = client.post(
        "/api/v1/dispatcher/overrides",
        json=payload_invalid_code,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response2.status_code == 422

# Test 5: Override creates dispatcher_overrides record
def test_override_creates_dispatcher_overrides_record():
    token = get_dispatcher_token()
    payload = {
        "delivery_id": "DEL-1002",
        "new_status": "delivered",
        "reason_code": "GPS_UNAVAILABLE",
        "reason_text": "Rider GPS tower signal dropped in subterranean parking."
    }
    response = client.post(
        "/api/v1/dispatcher/overrides",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201

    db = SessionLocal()
    override_rec = db.query(DispatcherOverride).filter(DispatcherOverride.delivery_id == "DEL-1002").first()
    assert override_rec is not None
    assert override_rec.reason_code == "GPS_UNAVAILABLE"
    assert override_rec.new_status == "delivered"
    db.close()

# Test 6: Override creates audit_logs record
def test_override_creates_audit_logs_record():
    token = get_dispatcher_token()
    payload = {
        "delivery_id": "DEL-1002",
        "new_status": "delivered",
        "reason_code": "NETWORK_FAILURE",
        "reason_text": "Cellular network latency caused upload timeout."
    }
    client.post(
        "/api/v1/dispatcher/overrides",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    db = SessionLocal()
    audit_rec = db.query(AuditLog).filter(
        AuditLog.entity_id == "DEL-1002",
        AuditLog.action == "dispatcher_override"
    ).first()
    assert audit_rec is not None
    assert audit_rec.entity_type == "delivery"
    assert "NETWORK_FAILURE" in audit_rec.reason
    db.close()

# Test 7: Previous status and new status are preserved
def test_previous_and_new_status_preserved():
    token = get_dispatcher_token()

    # Initial status of DEL-1002 in seed db is DISPUTED
    payload = {
        "delivery_id": "DEL-1002",
        "new_status": "delivered",
        "reason_code": "CUSTOMER_CONFIRMED_RECEIPT",
        "reason_text": "Verified with customer"
    }
    resp = client.post(
        "/api/v1/dispatcher/overrides",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 201

    db = SessionLocal()
    override_rec = db.query(DispatcherOverride).filter(DispatcherOverride.delivery_id == "DEL-1002").first()
    assert override_rec.previous_status in ["in_transit", "disputed", "needs_review"]
    assert override_rec.new_status == "delivered"
    db.close()

# Test 8: Multiple overrides preserve complete history
def test_multiple_overrides_preserve_complete_history():
    token = get_dispatcher_token()

    # Override 1: IN_TRANSIT -> DELIVERED
    client.post(
        "/api/v1/dispatcher/overrides",
        json={
            "delivery_id": "DEL-1002",
            "new_status": "delivered",
            "reason_code": "CUSTOMER_CONFIRMED_RECEIPT",
            "reason_text": "Override 1 confirmed"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    # Override 2: DELIVERED -> NEEDS_REVIEW
    client.post(
        "/api/v1/dispatcher/overrides",
        json={
            "delivery_id": "DEL-1002",
            "new_status": "needs_review",
            "reason_code": "EVIDENCE_EXCEPTION",
            "reason_text": "Override 2 re-evaluation"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    # Fetch History
    hist_resp = client.get(
        "/api/v1/dispatcher/deliveries/DEL-1002/history",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert hist_resp.status_code == 200
    events = hist_resp.json()

    overrides_in_history = [e for e in events if e["event_type"] == "OVERRIDE"]
    assert len(overrides_in_history) >= 2
    assert overrides_in_history[-2]["new_status"] == "delivered"
    assert overrides_in_history[-1]["previous_status"] == "delivered"
    assert overrides_in_history[-1]["new_status"] == "needs_review"

# Test 9: Unauthorized users cannot access history
def test_unauthorized_user_cannot_access_history():
    rider_token = get_rider_token()
    cust_token = get_customer_token()

    r1 = client.get("/api/v1/dispatcher/deliveries/DEL-1002/history", headers={"Authorization": f"Bearer {rider_token}"})
    assert r1.status_code == 403

    r2 = client.get("/api/v1/dispatcher/deliveries/DEL-1002/history", headers={"Authorization": f"Bearer {cust_token}"})
    assert r2.status_code == 403

# Test 10: Admin can access dispatcher history
def test_admin_can_access_dispatcher_history():
    admin_token = get_admin_token()
    resp = client.get(
        "/api/v1/dispatcher/deliveries/DEL-1002/history",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)
