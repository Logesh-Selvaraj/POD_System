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
    """
    Evidence Quality Engine (EQE) — deterministic, multi-factor scoring
    pipeline that converts raw submission data into a 0–100 quality score
    and routes the delivery to one of three triage bands.

    SCORING RUBRIC (total: 100 pts)
    ┌────────────┬──────┬────────────────────────────────────────────────────┐
    │ Component  │ Max  │ Rationale                                          │
    ├────────────┼──────┼────────────────────────────────────────────────────┤
    │ Photo      │  25  │ OpenCV blur + brightness; unreadable = no evidence │
    │ GPS        │  25  │ Haversine ≤ 150 m; mismatch = possible fraud       │
    │ Timestamp  │  20  │ ISO-8601 presence; missing = tampered submission   │
    │ Signature  │  20  │ Canvas base64 present; absent = unconfirmed receipt│
    │ OTP        │  10  │ Exact string match; wrong = wrong recipient        │
    └────────────┴──────┴────────────────────────────────────────────────────┘

    CLASSIFICATION THRESHOLDS
        ≥ 90 → ACCEPTED          : Automated delivery completion.
        ≥ 70 → NEEDS_MANUAL_REVIEW: Routed to Dispatcher Queue.
        < 70 → DISPUTE           : Flagged for investigation.

    The threshold values (90/70) were calibrated against the Review-1
    benchmark dataset (50 synthetic scenarios) to minimise both false
    positives (legitimate deliveries wrongly flagged) and false negatives
    (fraudulent deliveries wrongly accepted).

    OFFLINE CAPTURE DETECTION
        If captured GPS coordinates are null or exactly (0.0, 0.0) the
        submission is tagged is_offline_capture=True and gps_score=0.
        This prevents a rider from submitting null coordinates and claiming
        GPS credit.  The Dispatcher can then evaluate contextual evidence
        and override if appropriate.
    """

    # ── 1. Photo validation (Max 25 pts) ────────────────────────────────────
    # Delegates to opencv_validator which applies the Laplacian blur check
    # and mean brightness check.  See opencv_validator.py for threshold docs.
    photo_eval = validate_image(image_bytes)
    photo_score = photo_eval["photo_score"]

    # ── 2. GPS validation (Max 25 pts) ──────────────────────────────────────
    is_offline_capture = False
    gps_valid = False
    distance_m = None
    gps_score = 0.0

    if captured_latitude is None or captured_longitude is None or (captured_latitude == 0.0 and captured_longitude == 0.0):
        # Zero-coordinate sentinel: the device had no GPS fix at capture time.
        # Marking is_offline_capture allows the Dispatcher to apply the
        # "indoor delivery" override pattern without falsely penalising riders
        # operating in GPS-dead zones (basements, underground car parks).
        is_offline_capture = True
        gps_valid = False
        gps_score = 0.0
    else:
        # Haversine great-circle distance in metres between captured
        # coordinates and the delivery destination registered at order creation.
        distance_m = haversine_distance(
            captured_latitude, captured_longitude,
            target_latitude, target_longitude
        )
        if distance_m <= settings.GPS_MISMATCH_THRESHOLD_METERS:
            # Within 150 m of the destination: rider is plausibly on-site.
            gps_valid = True
            gps_score = 25.0
        else:
            # Beyond threshold: coordinates do not match destination.
            # Full penalty applied; a partial score is not warranted because
            # a far-off submission is either GPS drift or deliberate fraud.
            gps_valid = False
            gps_score = 0.0

    # ── 3. Timestamp validation (Max 20 pts) ────────────────────────────────
    # The timestamp must be a valid datetime object (parsed in the router from
    # the ISO-8601 string sent by the client).  A missing timestamp is a sign
    # of either a client bug or evidence tampering, so it scores zero.
    # Future: add staleness check — reject timestamps older than N hours to
    # prevent replay attacks of old valid submissions.
    timestamp_valid = True
    if captured_timestamp is None:
        timestamp_valid = False
        timestamp_score = 0.0
    else:
        timestamp_score = 20.0

    # ── 4. Signature validation (Max 20 pts) ────────────────────────────────
    # has_signature is set by the router if the base64-encoded signature data
    # was non-empty and successfully decoded.  Binary present/absent scoring
    # is intentional: a partially drawn signature is still a signature,
    # and the canvas component requires the user to actively confirm the pad.
    signature_score = 20.0 if has_signature else 0.0

    # ── 5. OTP validation (Max 10 pts) ──────────────────────────────────────
    # Exact string comparison against the OTP code stored on the delivery
    # record at creation time.  The OTP is a 4-digit numeric code sent to
    # the customer's registered phone number via the SMS service.
    # A mismatch means either the wrong customer was served, or the rider is
    # attempting submission without proper recipient confirmation.
    # Score is deliberately binary (10 or 0) rather than partial, because any
    # deviation from the expected code represents a failed identity check.
    otp_valid = (otp_entered == target_otp) if otp_entered else False
    otp_score = 10.0 if otp_valid else 0.0

    # ── 6. Total Score Calculation (0–100) ──────────────────────────────────
    total_score = photo_score + gps_score + timestamp_score + signature_score + otp_score

    # ── 7. Quality Classification ────────────────────────────────────────────
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
