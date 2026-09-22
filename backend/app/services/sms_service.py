import logging
import re
from typing import Optional, Dict, Any
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class SMSNotConfiguredError(Exception):
    """Raised when an SMS provider is not configured."""
    pass

class SMSSendError(Exception):
    """Raised when sending an SMS fails via the provider."""
    pass

def is_sms_configured() -> bool:
    """
    Checks if an SMS service or provider credentials are fully configured.
    Returns False if no provider or credentials are set.
    """
    # 1. Explicit sandbox/mock mode
    if settings.SMS_PROVIDER and settings.SMS_PROVIDER.lower() in ["sandbox", "mock"]:
        return True

    # 2. Fast2SMS Provider
    if settings.FAST2SMS_API_KEY and settings.FAST2SMS_API_KEY.strip():
        return True

    # 3. Twilio Provider
    if (
        settings.TWILIO_ACCOUNT_SID and settings.TWILIO_ACCOUNT_SID.strip() and
        settings.TWILIO_AUTH_TOKEN and settings.TWILIO_AUTH_TOKEN.strip() and
        settings.TWILIO_FROM_NUMBER and settings.TWILIO_FROM_NUMBER.strip()
    ):
        return True

    # 4. Custom / Generic HTTP SMS Gateway
    if settings.SMS_API_URL and settings.SMS_API_URL.strip():
        return True

    return False

def clean_phone_number(phone: str) -> str:
    """Extract digits from phone number."""
    return re.sub(r"\D", "", phone)

def format_international_number(clean_digits: str, default_country_code: str = "+91") -> str:
    """Ensure standard E.164 phone formatting."""
    if clean_digits.startswith("91") and len(clean_digits) == 12:
        return f"+{clean_digits}"
    if len(clean_digits) == 10:
        return f"{default_country_code}{clean_digits}"
    return f"+{clean_digits}"

def send_otp_sms(
    phone_number: str,
    otp_code: str,
    customer_name: Optional[str] = None,
    delivery_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Dispatches a delivery verification OTP to the customer mobile number.
    Raises SMSNotConfiguredError if SMS service is not configured.
    Raises SMSSendError if sending fails.
    """
    if not is_sms_configured():
        logger.warning("Attempted to send OTP SMS, but no SMS provider is configured.")
        raise SMSNotConfiguredError("SMS service not configured")

    clean_digits = clean_phone_number(phone_number)
    if len(clean_digits) < 10:
        raise SMSSendError("Invalid phone number. Minimum 10 digits required.")

    formatted_10 = clean_digits[-10:]
    e164_phone = format_international_number(clean_digits)
    
    order_ref = f"for order #{delivery_id} " if delivery_id else ""
    message = f"Your Proof-of-Delivery verification OTP {order_ref}is: {otp_code}. Please share this code with your delivery rider only upon receiving your package."

    # 1. Sandbox / Mock Provider
    if settings.SMS_PROVIDER and settings.SMS_PROVIDER.lower() in ["sandbox", "mock"]:
        logger.info(f"[SANDBOX SMS] Sent OTP '{otp_code}' to {e164_phone} for order {delivery_id}")
        return {
            "success": True,
            "provider": "sandbox",
            "phone_number": e164_phone,
            "message": "OTP delivered via Sandbox SMS"
        }

    # 2. Fast2SMS Provider
    if settings.FAST2SMS_API_KEY and settings.FAST2SMS_API_KEY.strip():
        try:
            url = "https://www.fast2sms.com/dev/bulkV2"
            headers = {
                "authorization": settings.FAST2SMS_API_KEY.strip(),
                "Content-Type": "application/json"
            }
            payload = {
                "route": "otp",
                "variables_values": otp_code,
                "numbers": formatted_10
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                data = resp.json() if resp.status_code == 200 else {}
                if resp.status_code != 200 or not data.get("return", False):
                    err_msg = data.get("message", [resp.text])[0] if isinstance(data.get("message"), list) else data.get("message", resp.text)
                    raise SMSSendError(f"Fast2SMS API error: {err_msg}")
            return {
                "success": True,
                "provider": "fast2sms",
                "phone_number": e164_phone,
                "message": "OTP sent successfully via Fast2SMS"
            }
        except Exception as e:
            if isinstance(e, SMSSendError):
                raise
            raise SMSSendError(f"Fast2SMS request failed: {str(e)}")

    # 3. Twilio Provider
    if (
        settings.TWILIO_ACCOUNT_SID and settings.TWILIO_ACCOUNT_SID.strip() and
        settings.TWILIO_AUTH_TOKEN and settings.TWILIO_AUTH_TOKEN.strip() and
        settings.TWILIO_FROM_NUMBER and settings.TWILIO_FROM_NUMBER.strip()
    ):
        try:
            account_sid = settings.TWILIO_ACCOUNT_SID.strip()
            auth_token = settings.TWILIO_AUTH_TOKEN.strip()
            from_number = settings.TWILIO_FROM_NUMBER.strip()
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            data = {
                "To": e164_phone,
                "From": from_number,
                "Body": message
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, data=data, auth=(account_sid, auth_token))
                if resp.status_code not in (200, 201):
                    raise SMSSendError(f"Twilio API error ({resp.status_code}): {resp.text}")
            return {
                "success": True,
                "provider": "twilio",
                "phone_number": e164_phone,
                "message": "OTP sent successfully via Twilio"
            }
        except Exception as e:
            if isinstance(e, SMSSendError):
                raise
            raise SMSSendError(f"Twilio request failed: {str(e)}")

    # 4. Custom HTTP Webhook / Generic SMS Gateway
    if settings.SMS_API_URL and settings.SMS_API_URL.strip():
        try:
            headers = {"Content-Type": "application/json"}
            if settings.SMS_API_KEY:
                headers["Authorization"] = f"Bearer {settings.SMS_API_KEY.strip()}"
            payload = {
                "to": e164_phone,
                "phone_number": formatted_10,
                "otp": otp_code,
                "delivery_id": delivery_id,
                "message": message
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(settings.SMS_API_URL.strip(), json=payload, headers=headers)
                if resp.status_code not in (200, 201, 202):
                    raise SMSSendError(f"SMS Gateway error ({resp.status_code}): {resp.text}")
            return {
                "success": True,
                "provider": "custom_gateway",
                "phone_number": e164_phone,
                "message": "OTP sent successfully via SMS Gateway"
            }
        except Exception as e:
            if isinstance(e, SMSSendError):
                raise
            raise SMSSendError(f"Custom SMS Gateway request failed: {str(e)}")

    raise SMSNotConfiguredError("SMS service not configured")
