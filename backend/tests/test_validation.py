import pytest
import os
os.environ["USE_SQLITE"] = "true"

from fastapi.testclient import TestClient
from app.main import app
from app.init_db import init_db, SessionLocal
from app.models.validation import ValidationSession, ValidationResponse

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

def get_rider_token():
    return get_token("rider@pod.com", "rider123")

# 1. Create validation session test
def test_create_validation_session():
    payload = {
        "participant_code": "RIDER-01",
        "stakeholder_role": "rider",
        "validation_scenario": "Accept delivery and capture complete evidence"
    }
    response = client.post("/api/v1/validation/sessions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["stakeholder_role"] == "rider"

# 2. Submit valid rating test
def test_submit_valid_rating():
    # Create session first
    sess_resp = client.post("/api/v1/validation/sessions", json={
        "stakeholder_role": "rider",
        "validation_scenario": "Test Scenario"
    })
    session_id = sess_resp.json()["id"]

    # Submit Q1 rating
    response = client.post("/api/v1/validation/responses", json={
        "session_id": session_id,
        "question_id": "Q1",
        "rating": 4,
        "comment": "Very straightforward."
    })
    assert response.status_code == 201
    assert response.json()["rating"] == 4

# 3. Reject rating below 1 test
def test_reject_rating_below_1():
    sess_resp = client.post("/api/v1/validation/sessions", json={
        "stakeholder_role": "rider",
        "validation_scenario": "Test Scenario"
    })
    session_id = sess_resp.json()["id"]

    response = client.post("/api/v1/validation/responses", json={
        "session_id": session_id,
        "question_id": "Q1",
        "rating": 0
    })
    assert response.status_code == 422

# 4. Reject rating above 5 test
def test_reject_rating_above_5():
    sess_resp = client.post("/api/v1/validation/sessions", json={
        "stakeholder_role": "rider",
        "validation_scenario": "Test Scenario"
    })
    session_id = sess_resp.json()["id"]

    response = client.post("/api/v1/validation/responses", json={
        "session_id": session_id,
        "question_id": "Q1",
        "rating": 6
    })
    assert response.status_code == 422

# 5. Reject invalid question ID test
def test_reject_invalid_question_id():
    sess_resp = client.post("/api/v1/validation/sessions", json={
        "stakeholder_role": "rider",
        "validation_scenario": "Test Scenario"
    })
    session_id = sess_resp.json()["id"]

    # Bad question ID formats
    for bad_q in ["Q0", "Q11", "invalid_q", "Q01"]:
        response = client.post("/api/v1/validation/responses", json={
            "session_id": session_id,
            "question_id": bad_q,
            "rating": 5
        })
        assert response.status_code == 422

# 6. Reject invalid stakeholder role test
def test_reject_invalid_stakeholder_role():
    response = client.post("/api/v1/validation/sessions", json={
        "participant_code": "BAD-ROLE",
        "stakeholder_role": "super-admin",
        "validation_scenario": "Scenario text"
    })
    assert response.status_code == 422

# 7. Admin can view validation summary test
def test_admin_can_view_validation_summary():
    token = get_admin_token()
    response = client.get("/api/v1/validation/admin/summary", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "total_participants" in response.json()

# 8. Non-admin cannot view validation summary test
def test_non_admin_cannot_view_validation_summary():
    token = get_rider_token()
    response = client.get("/api/v1/validation/admin/summary", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

# 9. Empty validation dataset returns an empty state test
def test_empty_validation_dataset_returns_empty_state():
    token = get_admin_token()
    # Empty DB
    db = SessionLocal()
    try:
        db.query(ValidationResponse).delete()
        db.query(ValidationSession).delete()
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/validation/admin/summary", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_participants"] == 0
    assert data["average_overall_rating"] == 0.0

# 10. Summary calculations match stored responses test
def test_summary_calculations_match_stored_responses():
    token = get_admin_token()

    # Create 2 sessions
    sess1 = client.post("/api/v1/validation/sessions", json={"stakeholder_role": "rider", "validation_scenario": "Scenario 1"}).json()["id"]
    sess2 = client.post("/api/v1/validation/sessions", json={"stakeholder_role": "customer", "validation_scenario": "Scenario 2"}).json()["id"]

    # Submit ratings
    client.post("/api/v1/validation/responses", json={"session_id": sess1, "question_id": "Q1", "rating": 5})
    client.post("/api/v1/validation/responses", json={"session_id": sess2, "question_id": "Q1", "rating": 3})

    summary = client.get("/api/v1/validation/admin/summary", headers={"Authorization": f"Bearer {token}"}).json()
    assert summary["total_participants"] == 2
    assert summary["completed_sessions"] == 2
    assert summary["average_overall_rating"] == 4.0 # (5 + 3)/2
