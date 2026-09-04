import pytest
import numpy as np
import cv2
from datetime import datetime

from app.services.quality_engine import evaluate_evidence
from app.models.evidence import QualityClassification

def generate_sample_image_bytes(blur=False):
    # Create a simple synthetic image with gray background (brightness ~128)
    img = np.full((300, 300, 3), 128, dtype=np.uint8)
    # Add text & shapes to create sharp edges for Laplacian variance
    cv2.putText(img, "POD TEST PROOF", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.rectangle(img, (50, 50), (250, 250), (0, 0, 255), 3)
    
    if blur:
        img = cv2.GaussianBlur(img, (25, 25), 0)
        
    _, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes()

def test_quality_engine_perfect_score():
    img_bytes = generate_sample_image_bytes(blur=False)
    
    # Target location: (12.971598, 77.594566)
    # Captured location: exact target (0 meters distance)
    result = evaluate_evidence(
        image_bytes=img_bytes,
        has_signature=True,
        captured_latitude=12.971598,
        captured_longitude=77.594566,
        captured_timestamp=datetime.utcnow(),
        otp_entered="4829",
        target_latitude=12.971598,
        target_longitude=77.594566,
        target_otp="4829"
    )

    assert result["photo_score"] == 25.0
    assert result["gps_score"] == 25.0
    assert result["timestamp_score"] == 20.0
    assert result["signature_score"] == 20.0
    assert result["otp_score"] == 10.0
    assert result["total_quality_score"] == 100.0
    assert result["classification"] == QualityClassification.ACCEPTED
    assert result["is_offline_capture"] == False

def test_quality_engine_missing_gps_offline():
    img_bytes = generate_sample_image_bytes(blur=False)
    
    # Missing GPS coordinates (None)
    result = evaluate_evidence(
        image_bytes=img_bytes,
        has_signature=True,
        captured_latitude=None,
        captured_longitude=None,
        captured_timestamp=datetime.utcnow(),
        otp_entered="4829",
        target_latitude=12.971598,
        target_longitude=77.594566,
        target_otp="4829"
    )

    assert result["gps_score"] == 0.0
    assert result["is_offline_capture"] == True
    # Photo(25) + Timestamp(20) + Signature(20) + OTP(10) = 75 pts
    assert result["total_quality_score"] == 75.0
    assert result["classification"] == QualityClassification.NEEDS_MANUAL_REVIEW

def test_quality_engine_gps_mismatch_dispute():
    img_bytes = generate_sample_image_bytes(blur=True) # Blurred photo
    
    # Distance > 150 meters away (approx 5 km away)
    result = evaluate_evidence(
        image_bytes=img_bytes,
        has_signature=False,
        captured_latitude=13.000000,
        captured_longitude=77.600000,
        captured_timestamp=datetime.utcnow(),
        otp_entered="0000", # Wrong OTP
        target_latitude=12.971598,
        target_longitude=77.594566,
        target_otp="4829"
    )

    assert result["gps_valid"] == False
    assert result["gps_score"] == 0.0
    assert result["otp_valid"] == False
    assert result["signature_score"] == 0.0
    assert result["total_quality_score"] < 70.0
    assert result["classification"] == QualityClassification.DISPUTE
