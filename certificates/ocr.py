"""
OCR module (disabled for deployment).
This file replaces the heavy EasyOCR and fuzzy dependencies with a lightweight stub.
"""

from datetime import datetime

ALLOWED_BARANGAY = "longos"

def extract_from_image(image_bytes, bypass_barangay_check=False, is_authorized=False):
    """
    Dummy OCR extractor for deployment. Returns a safe, empty result.
    """
    return {
        "id_number": "",
        "full_name": "",
        "address": "",
        "age": "",
        "id_type": "Disabled",
        "raw_lines": [],
        "warning": "OCR is disabled on this deployment. Please enter data manually.",
        "confidence": 0.0,
        "detected_id": "disabled"
    }

def validate_barangay(addr_text, bypass=False, is_authorized=False):
    # Always return True in disabled mode to avoid blocking flows if bypass is used
    return True, ""
