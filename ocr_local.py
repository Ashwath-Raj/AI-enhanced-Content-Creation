import pytesseract
from PIL import Image
import json
import sys
import os
import cv2
import numpy as np
from pdf2image import convert_from_path
import tempfile


# -----------------------------
# IMAGE PREPROCESSING
# -----------------------------
def preprocess_image(image_path):
    img = cv2.imread(image_path)

    if img is None:
        raise ValueError("Unable to read image")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gray = cv2.resize(
        gray,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    _, thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return thresh


# -----------------------------
# QUALITY + GEMINI SIGNALS
# -----------------------------
def assess_quality(text, path, page_count=1):
    warnings = []
    confidence = 1.0

    text_len = len(text)

    if text_len < 100:
        warnings.append("short_text")
        confidence -= 0.3

    non_alpha_ratio = sum(
        1 for c in text if not c.isalnum() and not c.isspace()
    ) / max(text_len, 1)

    if non_alpha_ratio > 0.25:
        warnings.append("low_confidence_text")
        confidence -= 0.4

    try:
        img = Image.open(path)
        w, h = img.size
        if w < 800 or h < 800:
            warnings.append("low_resolution")
            confidence -= 0.2
    except:
        pass  # PDFs land here

    confidence = max(round(confidence, 2), 0.0)

    # ---- Gemini-facing signals ----
    if confidence > 0.8:
        noise_level = "low"
        llm_mode = "creative"
    elif confidence > 0.5:
        noise_level = "medium"
        llm_mode = "normal"
    else:
        noise_level = "high"
        llm_mode = "strict"

    avg_chars_per_page = int(text_len / max(page_count, 1))

    if avg_chars_per_page > 2500:
        text_density = "high"
    elif avg_chars_per_page > 800:
        text_density = "medium"
    else:
        text_density = "low"

    ocr_meta = {
        "input_type": "pdf" if page_count > 1 else "image",
        "page_count": page_count,
        "noise_level": noise_level,
        "recommended_llm_mode": llm_mode,
        "text_density": text_density,
        "avg_chars_per_page": avg_chars_per_page
    }

    return confidence, warnings, ocr_meta


# -----------------------------
# IMAGE OCR
# -----------------------------
def run_image_ocr(image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError("File not found")

    processed = preprocess_image(image_path)
    text = pytesseract.image_to_string(processed).strip()

    if not text:
        return {
            "schema_version": "1.2",
            "text": "",
            "overall_confidence": 0.0,
            "warnings": ["no_text_detected"],
            "ocr_meta": {
                "input_type": "image",
                "page_count": 1,
                "noise_level": "high",
                "recommended_llm_mode": "strict",
                "text_density": "low",
                "avg_chars_per_page": 0
            }
        }

    confidence, warnings, ocr_meta = assess_quality(text, image_path, page_count=1)

    return {
        "schema_version": "1.2",
        "text": text,
        "overall_confidence": confidence,
        "warnings": warnings,
        "ocr_meta": ocr_meta
    }


# -----------------------------
# PDF OCR
# -----------------------------
def run_pdf_ocr(pdf_path):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError("File not found")

    all_text = []
    warnings = []

    pages = convert_from_path(pdf_path, dpi=300)
    page_count = len(pages)

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, page in enumerate(pages):
            page_path = os.path.join(tmpdir, f"page_{i}.png")
            page.save(page_path, "PNG")

            processed = preprocess_image(page_path)
            text = pytesseract.image_to_string(processed).strip()

            if text:
                all_text.append(text)
            else:
                warnings.append(f"no_text_page_{i+1}")

    full_text = "\n\n".join(all_text)

    if not full_text:
        return {
            "schema_version": "1.2",
            "text": "",
            "overall_confidence": 0.0,
            "warnings": ["no_text_detected"],
            "ocr_meta": {
                "input_type": "pdf",
                "page_count": page_count,
                "noise_level": "high",
                "recommended_llm_mode": "strict",
                "text_density": "low",
                "avg_chars_per_page": 0
            }
        }

    confidence, quality_warnings, ocr_meta = assess_quality(
        full_text, pdf_path, page_count=page_count
    )

    return {
        "schema_version": "1.2",
        "text": full_text,
        "overall_confidence": confidence,
        "warnings": list(set(warnings + quality_warnings)),
        "ocr_meta": ocr_meta
    }


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python ocr_local.py <image_or_pdf_path>")
        sys.exit(1)

    path = sys.argv[1]

    if path.lower().endswith(".pdf"):
        output = run_pdf_ocr(path)
    else:
        output = run_image_ocr(path)

    print(json.dumps(output, indent=2))
