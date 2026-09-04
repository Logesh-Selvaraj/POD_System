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

def test_login_success():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "rider@pod.com", "password": "rider123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "rider"

def test_login_invalid_password():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "rider@pod.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_get_me_with_jwt():
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@pod.com", "password": "admin123"}
    )
    token = login_resp.json()["access_token"]
    
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "admin@pod.com"
    assert me_resp.json()["role"] == "admin"
