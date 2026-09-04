import pytest
import os
os.environ["USE_SQLITE"] = "true"

from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from app.main import app
from app.init_db import init_db, SessionLocal
from app.models.user import User, UserRole
from app.models.delivery import Delivery, DeliveryStatus
from app.models.evidence import Evidence, QualityClassification
from app.models.dispute import Dispute

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

def get_admin_token():
    return get_token("admin@pod.com", "admin123")

def get_dispatcher_token():
    return get_token("dispatcher@pod.com", "dispatcher123")

def get_rider_token():
    return get_token("rider@pod.com", "rider123")

def get_customer_token():
    return get_token("customer@pod.com", "customer123")

def get_restaurant_token():
    return get_token("restaurant@pod.com", "restaurant123")

# RBAC tests: Admin can access, others receive 403
def test_admin_can_access_analytics():
    token = get_admin_token()
    response = client.get("/api/v1/admin/analytics", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "total_deliveries" in response.json()

def test_unauthorized_roles_receive_403():
    for get_token_fn in [get_rider_token, get_customer_token, get_dispatcher_token, get_restaurant_token]:
        token = get_token_fn()
        response = client.get("/api/v1/admin/analytics", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

# Correct calculations tests
def test_analytics_correct_metrics():
    # We should have some seeded data from init_db.
    # Let's verify metrics are returned and match database queries
    token = get_admin_token()
    response = client.get("/api/v1/admin/analytics", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    
    db = SessionLocal()
    try:
        del_count = db.query(Delivery).count()
        disp_count = db.query(Dispute).count()
        evidences = db.query(Evidence).all()
        avg_score = sum(ev.total_quality_score for ev in evidences) / len(evidences) if evidences else None

        assert data["total_deliveries"] == del_count
        assert data["dispute_analytics"]["total_disputes"] == disp_count
        if avg_score is not None:
            assert abs(data["average_evidence_score"] - avg_score) < 0.01
        else:
            assert data["average_evidence_score"] is None
    finally:
        db.close()

# Date filtering tests
def test_date_filtering():
    token = get_admin_token()
    
    # 1. Filter with narrow date range that should have no items
    resp_empty = client.get(
        "/api/v1/admin/analytics?from_date=2000-01-01&to_date=2000-01-02",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp_empty.status_code == 200
    assert resp_empty.json()["total_deliveries"] == 0

    # 2. Filter with broad range that should include items
    resp_all = client.get(
        f"/api/v1/admin/analytics?from_date=2020-01-01&to_date=2030-12-31",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp_all.status_code == 200
    assert resp_all.json()["total_deliveries"] > 0

def test_invalid_date_range_returns_422():
    token = get_admin_token()
    
    # Invalid format
    resp1 = client.get("/api/v1/admin/analytics?from_date=invalid-date", headers={"Authorization": f"Bearer {token}"})
    assert resp1.status_code == 422

    # from_date after to_date
    resp2 = client.get("/api/v1/admin/analytics?from_date=2026-08-12&to_date=2026-08-11", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 422

def test_empty_dataset_returns_valid_empty_analytics():
    # Empty DB manually
    db = SessionLocal()
    try:
        db.query(Dispute).delete()
        db.query(Evidence).delete()
        db.query(Delivery).delete()
        db.commit()
    finally:
        db.close()

    token = get_admin_token()
    response = client.get("/api/v1/admin/analytics", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_deliveries"] == 0
    assert data["average_evidence_score"] is None
    assert len(data["rider_performance"]) == 0
    assert data["dispute_analytics"]["total_disputes"] == 0
