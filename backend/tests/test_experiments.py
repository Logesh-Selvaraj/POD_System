import pytest
import os
os.environ["USE_SQLITE"] = "true"

from fastapi.testclient import TestClient
from app.main import app
from app.init_db import init_db, SessionLocal
from app.models.experiment import ExperimentCase, ExperimentResult, ExperimentRun
from app.routers.experiments import compute_metrics

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

# 1. Baseline valid delivery logic test
def test_baseline_valid_delivery():
    # If photo exists and status is complete (ACCEPTED ground truth), baseline classifies as ACCEPTED.
    token = get_admin_token()
    run_resp = client.post("/api/v1/admin/experiments/run", headers={"Authorization": f"Bearer {token}"})
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    db = SessionLocal()
    try:
        # Check CASE-1001 (Fully Valid Delivery)
        res = db.query(ExperimentResult).filter(
            ExperimentResult.experiment_run_id == run_id,
            ExperimentResult.case_id == "CASE-1001",
            ExperimentResult.system_type == "BASELINE"
        ).first()
        assert res.final_classification == "ACCEPTED"
        assert res.evidence_valid is True
    finally:
        db.close()

# 2. Baseline missing photo logic test
def test_baseline_missing_photo():
    # If photo is none, baseline is DISPUTE.
    db = SessionLocal()
    try:
        # We manually modify/add a case without photo
        case = ExperimentCase(
            case_id="CASE-TEST-MISSING-PHOTO",
            scenario_type="No Photo Test",
            photo_quality="none",
            gps_available=True,
            expected_delivery_outcome="ACCEPTED"
        )
        db.add(case)
        db.commit()
    finally:
        db.close()

    token = get_admin_token()
    run_resp = client.post("/api/v1/admin/experiments/run", headers={"Authorization": f"Bearer {token}"})
    run_id = run_resp.json()["id"]

    db = SessionLocal()
    try:
        res = db.query(ExperimentResult).filter(
            ExperimentResult.experiment_run_id == run_id,
            ExperimentResult.case_id == "CASE-TEST-MISSING-PHOTO",
            ExperimentResult.system_type == "BASELINE"
        ).first()
        assert res.final_classification == "DISPUTE"
    finally:
        db.close()

# 3. Proposed fully valid delivery test
def test_proposed_fully_valid_delivery():
    token = get_admin_token()
    run_resp = client.post("/api/v1/admin/experiments/run", headers={"Authorization": f"Bearer {token}"})
    run_id = run_resp.json()["id"]

    db = SessionLocal()
    try:
        res = db.query(ExperimentResult).filter(
            ExperimentResult.experiment_run_id == run_id,
            ExperimentResult.case_id == "CASE-1001",
            ExperimentResult.system_type == "PROPOSED"
        ).first()
        assert res.final_classification == "ACCEPTED"
    finally:
        db.close()

# 4. Proposed blurred photo test
def test_proposed_blurred_photo():
    token = get_admin_token()
    run_resp = client.post("/api/v1/admin/experiments/run", headers={"Authorization": f"Bearer {token}"})
    run_id = run_resp.json()["id"]

    db = SessionLocal()
    try:
        # CASE-1011 (Blurred Photo)
        res = db.query(ExperimentResult).filter(
            ExperimentResult.experiment_run_id == run_id,
            ExperimentResult.case_id == "CASE-1011",
            ExperimentResult.system_type == "PROPOSED"
        ).first()
        # Photo=12.5 + GPS=25 + Time=20 + Sig=20 + OTP=10 = 87.5 (NEEDS_MANUAL_REVIEW)
        assert res.final_classification == "NEEDS_MANUAL_REVIEW"
    finally:
        db.close()

# 5. Proposed missing GPS test
def test_proposed_missing_gps():
    token = get_admin_token()
    run_resp = client.post("/api/v1/admin/experiments/run", headers={"Authorization": f"Bearer {token}"})
    run_id = run_resp.json()["id"]

    db = SessionLocal()
    try:
        # CASE-1015 (Missing GPS)
        res = db.query(ExperimentResult).filter(
            ExperimentResult.experiment_run_id == run_id,
            ExperimentResult.case_id == "CASE-1015",
            ExperimentResult.system_type == "PROPOSED"
        ).first()
        # Photo=25 + GPS=0 + Time=20 + Sig=20 + OTP=10 = 75 (NEEDS_MANUAL_REVIEW)
        assert res.final_classification == "NEEDS_MANUAL_REVIEW"
    finally:
        db.close()

# 6. Proposed GPS mismatch test
def test_proposed_gps_mismatch():
    token = get_admin_token()
    run_resp = client.post("/api/v1/admin/experiments/run", headers={"Authorization": f"Bearer {token}"})
    run_id = run_resp.json()["id"]

    db = SessionLocal()
    try:
        # CASE-1019 (GPS Mismatch, > 150m)
        res = db.query(ExperimentResult).filter(
            ExperimentResult.experiment_run_id == run_id,
            ExperimentResult.case_id == "CASE-1019",
            ExperimentResult.system_type == "PROPOSED"
        ).first()
        # Photo=25 + GPS=0 + Time=20 + Sig=20 + OTP=10 = 75 (NEEDS_MANUAL_REVIEW)
        # But wait, ground truth expected outcome is DISPUTE because GPS is mismatched.
        # Let's make sure it is resolved/classified correctly.
        assert res.final_classification == "NEEDS_MANUAL_REVIEW"
    finally:
        db.close()

# 7. Proposed missing signature test
def test_proposed_missing_signature():
    token = get_admin_token()
    run_resp = client.post("/api/v1/admin/experiments/run", headers={"Authorization": f"Bearer {token}"})
    run_id = run_resp.json()["id"]

    db = SessionLocal()
    try:
        # CASE-1026 (Missing Signature)
        res = db.query(ExperimentResult).filter(
            ExperimentResult.experiment_run_id == run_id,
            ExperimentResult.case_id == "CASE-1026",
            ExperimentResult.system_type == "PROPOSED"
        ).first()
        # Photo=25 + GPS=25 + Time=20 + Sig=0 + OTP=10 = 80 (NEEDS_MANUAL_REVIEW)
        assert res.final_classification == "NEEDS_MANUAL_REVIEW"
    finally:
        db.close()

# 8. Proposed invalid OTP test
def test_proposed_invalid_otp():
    token = get_admin_token()
    run_resp = client.post("/api/v1/admin/experiments/run", headers={"Authorization": f"Bearer {token}"})
    run_id = run_resp.json()["id"]

    db = SessionLocal()
    try:
        # CASE-1029 (Invalid OTP)
        res = db.query(ExperimentResult).filter(
            ExperimentResult.experiment_run_id == run_id,
            ExperimentResult.case_id == "CASE-1029",
            ExperimentResult.system_type == "PROPOSED"
        ).first()
        # Photo=25 + GPS=25 + Time=20 + Sig=20 + OTP=0 = 90 (ACCEPTED)
        # Wait, if OTP is invalid but others are fully valid, score is 90 -> ACCEPTED.
        assert res.final_classification == "ACCEPTED"
    finally:
        db.close()

# 9. Metric calculation test
def test_experiment_metric_calculation():
    token = get_admin_token()
    run_resp = client.post("/api/v1/admin/experiments/run", headers={"Authorization": f"Bearer {token}"})
    run_id = run_resp.json()["id"]

    detail_resp = client.get(f"/api/v1/admin/experiments/{run_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail_resp.status_code == 200
    data = detail_resp.json()
    assert "baseline_metrics" in data
    assert "proposed_metrics" in data
    assert data["baseline_metrics"]["accuracy"] > 0

# 10. Baseline vs proposed comparison test
def test_baseline_vs_proposed_comparison():
    token = get_admin_token()
    run_resp = client.post("/api/v1/admin/experiments/run", headers={"Authorization": f"Bearer {token}"})
    run_id = run_resp.json()["id"]

    detail_resp = client.get(f"/api/v1/admin/experiments/{run_id}", headers={"Authorization": f"Bearer {token}"})
    data = detail_resp.json()
    assert "comparison_table" in data
    assert len(data["comparison_table"]) > 0

# 11. Admin-only experiment API test
def test_admin_only_experiment_api():
    token = get_admin_token()
    response = client.get("/api/v1/admin/experiments", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

# 12. Non-admin receives 403 test
def test_non_admin_receives_403():
    token = get_rider_token()
    response = client.get("/api/v1/admin/experiments", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

# 13. Empty experiment result handling test
def test_empty_experiment_result_handling():
    # If no results exist yet
    token = get_admin_token()
    # Trigger runs list when database is populated but no run executed
    response = client.get("/api/v1/admin/experiments", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

# 14. Zero-denominator improvement handling test
def test_zero_denominator_improvement_handling():
    # Manually compute metrics with empty scenario results
    metrics = compute_metrics([], [])
    assert metrics.accuracy == 0.0
    assert metrics.dispute_resolution_rate == 0.0
