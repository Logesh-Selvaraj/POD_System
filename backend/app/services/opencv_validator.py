import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import cv2
import numpy as np
from app.core.config import settings

def validate_image(image_bytes: bytes) -> dict:
    """
    Perform OpenCV Laplacian variance blur check and brightness check on raw image bytes.
    Returns dictionary with blur_score, brightness_score, and photo_score (max 25).

    BLUR CHECK — Laplacian Variance (blur_score):
        The Laplacian operator computes the second derivative of the image.
        A sharp image has strong edges that produce a high variance; a blurry
        image has smoothed gradients that produce a low variance.
        Threshold: OPENCV_BLUR_THRESHOLD (default 100.0).  Values below this
        threshold indicate that the photo is too blurry to be accepted as POD
        evidence, because important details (address labels, recipient face)
        would be unreadable.

    BRIGHTNESS CHECK — Mean pixel intensity (brightness_score):
        An image that is nearly black (very low mean) or fully white (very high
        mean) contains no recoverable information.  The accepted band is
        [OPENCV_BRIGHTNESS_MIN, OPENCV_BRIGHTNESS_MAX] (default 40–220).
        Values outside this range flag night-time captures without flash, or
        overexposed images where the subject is washed out.

    PHOTO SCORING (max 25 pts):
        Both checks pass → 25.0  (full credit: identifiable, well-lit photo)
        One check passes  → 12.5  (partial credit: borderline quality)
        Neither passes    →  0.0  (image is unusable as evidence)

    The partial-credit band (12.5) is intentional: a slightly blurry but
    correctly-lit photo still provides more information than nothing, so it
    routes to NEEDS_MANUAL_REVIEW rather than an immediate DISPUTE.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # If OpenCV cannot decode the bytes the upload is corrupt or unsupported.
    # Return zero scores so the EQE treats this as a missing photo.
    if img is None:
        return {
            "blur_score": 0.0,
            "brightness_score": 0.0,
            "blur_pass": False,
            "brightness_pass": False,
            "photo_score": 0.0
        }

    # Convert to grayscale: colour information is irrelevant for blur and
    # brightness measurements, and grayscale reduces computation cost.
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Blur Check (Laplacian Variance)
    # cv2.CV_64F: 64-bit float prevents overflow from large variance values.
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    blur_pass = blur_score >= settings.OPENCV_BLUR_THRESHOLD
    
    # 2. Brightness Check (Mean Pixel Intensity)
    # np.mean over the full grayscale image gives overall luminance [0, 255].
    brightness_score = float(np.mean(gray))
    brightness_pass = (
        settings.OPENCV_BRIGHTNESS_MIN <= brightness_score <= settings.OPENCV_BRIGHTNESS_MAX
    )
    
    # Photo score calculation (max 25 pts) — see docstring for rationale.
    photo_score = 0.0
    if blur_pass and brightness_pass:
        photo_score = 25.0
    elif blur_pass or brightness_pass:
        photo_score = 12.5
    else:
        photo_score = 0.0

    return {
        "blur_score": round(blur_score, 2),
        "brightness_score": round(brightness_score, 2),
        "blur_pass": blur_pass,
        "brightness_pass": brightness_pass,
        "photo_score": photo_score
    }
