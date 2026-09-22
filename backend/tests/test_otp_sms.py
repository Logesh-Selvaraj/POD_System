import pytest
import os
os.environ["USE_SQLITE"] = "true"

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.init_db import init_db
from app.core.config import settings
from app.services.sms_service import is_sms_configured, send_otp_sms, SMSNotConfiguredError, SMSSendError

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

def test_is_sms_configured_defaults_to_false_without_env():
    with patch.object(settings, "SMS_PROVIDER", None), \
         patch.object(settings, "FAST2SMS_API_KEY", None), \
         patch.object(settings, "TWILIO_ACCOUNT_SID", None), \
         patch.object(settings, "TWILIO_AUTH_TOKEN", None), \
         patch.object(settings, "TWILIO_FROM_NUMBER", None), \
         patch.object(settings, "SMS_API_URL", None), \
         patch.object(settings, "SMS_API_KEY", None):
        assert is_sms_configured() is False

def test_send_otp_raises_error_when_unconfigured():
    with patch.object(settings, "SMS_PROVIDER", None), \
         patch.object(settings, "FAST2SMS_API_KEY", None), \
         patch.object(settings, "TWILIO_ACCOUNT_SID", None), \
         patch.object(settings, "TWILIO_AUTH_TOKEN", None), \
         patch.object(settings, "TWILIO_FROM_NUMBER", None), \
         patch.object(settings, "SMS_API_URL", None), \
         patch.object(settings, "SMS_API_KEY", None):
        with pytest.raises(SMSNotConfiguredError, match="SMS service not configured"):
            send_otp_sms(phone_number="9876543210", otp_code="4829")

def test_api_send_otp_unconfigured_returns_503():
    token = get_rider_token()
    with patch.object(settings, "SMS_PROVIDER", None), \
         patch.object(settings, "FAST2SMS_API_KEY", None), \
         patch.object(settings, "TWILIO_ACCOUNT_SID", None), \
         patch.object(settings, "TWILIO_AUTH_TOKEN", None), \
         patch.object(settings, "TWILIO_FROM_NUMBER", None), \
         patch.object(settings, "SMS_API_URL", None), \
         patch.object(settings, "SMS_API_KEY", None):
        resp = client.post(
            "/api/v1/deliveries/DEL-1001/send-otp",
            json={"phone_number": "9876543210"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 503
        assert resp.json()["detail"] == "SMS service not configured"

def test_api_send_otp_nonexistent_delivery_returns_404():
    token = get_rider_token()
    resp = client.post(
        "/api/v1/deliveries/DEL-NONEXISTENT/send-otp",
        json={"phone_number": "9876543210"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404

def test_api_send_otp_invalid_phone_returns_400():
    token = get_rider_token()
    resp = client.post(
        "/api/v1/deliveries/DEL-1001/send-otp",
        json={"phone_number": "123"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400

def test_api_send_otp_sandbox_mode_success():
    token = get_rider_token()
    with patch.object(settings, "SMS_PROVIDER", "sandbox"):
        resp = client.post(
            "/api/v1/deliveries/DEL-1001/send-otp",
            json={"phone_number": "9876543210"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "OTP sent successfully"
        assert data["provider"] == "sandbox"
        # OTP code must NOT be leaked in the response payload
        assert "otp_code" not in data
        assert "4829" not in str(data)

def test_api_send_otp_fast2sms_mock_success():
    token = get_rider_token()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"return": True, "message": ["SMS sent successfully."]}

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.return_value = mock_resp

    with patch.object(settings, "SMS_PROVIDER", "fast2sms"), \
         patch.object(settings, "FAST2SMS_API_KEY", "mock_fast2sms_key"), \
         patch("app.services.sms_service.httpx.Client", return_value=mock_client_instance):
        resp = client.post(
            "/api/v1/deliveries/DEL-1001/send-otp",
            json={"phone_number": "9876543210"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["provider"] == "fast2sms"

def test_api_send_otp_twilio_mock_success():
    token = get_rider_token()
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.text = '{"sid": "SM12345"}'

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.return_value = mock_resp

    with patch.object(settings, "SMS_PROVIDER", "twilio"), \
         patch.object(settings, "TWILIO_ACCOUNT_SID", "AC123"), \
         patch.object(settings, "TWILIO_AUTH_TOKEN", "token123"), \
         patch.object(settings, "TWILIO_FROM_NUMBER", "+15005550006"), \
         patch("app.services.sms_service.httpx.Client", return_value=mock_client_instance):
        resp = client.post(
            "/api/v1/deliveries/DEL-1001/send-otp",
            json={"phone_number": "9876543210"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["provider"] == "twilio"
