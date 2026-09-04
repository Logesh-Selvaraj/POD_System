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
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return {
            "blur_score": 0.0,
            "brightness_score": 0.0,
            "blur_pass": False,
            "brightness_pass": False,
            "photo_score": 0.0
        }

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Blur Check (Laplacian Variance)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    blur_pass = blur_score >= settings.OPENCV_BLUR_THRESHOLD
    
    # 2. Brightness Check (Mean Pixel Intensity)
    brightness_score = float(np.mean(gray))
    brightness_pass = (
        settings.OPENCV_BRIGHTNESS_MIN <= brightness_score <= settings.OPENCV_BRIGHTNESS_MAX
    )
    
    # Photo score calculation (max 25 pts)
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
