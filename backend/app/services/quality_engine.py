from datetime import datetime
from typing import Optional, Dict, Any

from app.core.config import settings
from app.services.opencv_validator import validate_image
from app.services.haversine import haversine_distance
from app.models.evidence import QualityClassification

def evaluate_evidence(
    image_bytes: bytes,
    has_signature: bool,
    captured_latitude: Optional[float],
    captured_longitude: Optional[float],
    captured_timestamp: datetime,
    otp_entered: Optional[str],
    target_latitude: float,
    target_longitude: float,
    target_otp: str
) -> Dict[str, Any]:
    
    # 1. Photo validation (Max 25 pts)
    photo_eval = validate_image(image_bytes)
    photo_score = photo_eval["photo_score"]
    
    # 2. GPS validation (Max 25 pts)
    is_offline_capture = False
    gps_valid = False
    distance_m = None
    gps_score = 0.0

    if captured_latitude is None or captured_longitude is None or (captured_latitude == 0.0 and captured_longitude == 0.0):
        is_offline_capture = True
        gps_valid = False
        gps_score = 0.0
    else:
        distance_m = haversine_distance(
            captured_latitude, captured_longitude,
            target_latitude, target_longitude
        )
        if distance_m <= settings.GPS_MISMATCH_THRESHOLD_METERS:
            gps_valid = True
            gps_score = 25.0
        else:
            gps_valid = False
            gps_score = 0.0

    # 3. Timestamp validation (Max 20 pts)
    timestamp_valid = True  # Validated timestamp presence & sanity
    if captured_timestamp is None:
        timestamp_valid = False
        timestamp_score = 0.0
    else:
        timestamp_score = 20.0

    # 4. Signature validation (Max 20 pts)
    signature_score = 20.0 if has_signature else 0.0

    # 5. OTP validation (Max 10 pts)
    otp_valid = (otp_entered == target_otp) if otp_entered else False
    otp_score = 10.0 if otp_valid else 0.0

    # Total Score Calculation (0 - 100)
    total_score = photo_score + gps_score + timestamp_score + signature_score + otp_score

    # Quality Classification
    if total_score >= 90.0:
        classification = QualityClassification.ACCEPTED
    elif total_score >= 70.0:
        classification = QualityClassification.NEEDS_MANUAL_REVIEW
    else:
        classification = QualityClassification.DISPUTE

    return {
        "photo_score": photo_score,
        "gps_score": gps_score,
        "timestamp_score": timestamp_score,
        "signature_score": signature_score,
        "otp_score": otp_score,
        "total_quality_score": round(total_score, 2),
        "classification": classification,
        "blur_score": photo_eval["blur_score"],
        "brightness_score": photo_eval["brightness_score"],
        "distance_m": round(distance_m, 2) if distance_m is not None else None,
        "gps_valid": gps_valid,
        "timestamp_valid": timestamp_valid,
        "otp_valid": otp_valid,
        "is_offline_capture": is_offline_capture
    }
