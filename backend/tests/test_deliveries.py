import pytest
import os
os.environ["USE_SQLITE"] = "true"

from fastapi.testclient import TestClient
from app.main import app
from app.init_db import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db(reset=True)

def get_rider_token():
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "rider@pod.com", "password": "rider123"}
    )
    return resp.json()["access_token"]

def test_get_assigned_deliveries():
    token = get_rider_token()
    response = client.get(
        "/api/v1/deliveries/assigned",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    deliveries = response.json()
    assert isinstance(deliveries, list)
    assert len(deliveries) >= 1
    assert deliveries[0]["id"] in ["DEL-1001", "DEL-1002"]

def test_get_delivery_by_id():
    token = get_rider_token()
    response = client.get(
        "/api/v1/deliveries/DEL-1001",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["customer_name"] == "Alice Smith"
    assert data["otp_code"] == "4829"
