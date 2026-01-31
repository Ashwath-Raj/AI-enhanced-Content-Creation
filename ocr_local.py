"""
ocr_local.py

Unified document ingestion + OCR service.

WHAT THIS FILE DOES:
- Accepts MANY reasonable file types (image, pdf, text, zip)
- Normalizes everything into ONE JSON output format
- Runs OCR only when needed
- Emits Gemini-aware metadata so LLMs don't hallucinate
- Designed to be wrapped by FastAPI later

SUPPORTED INPUTS:
- Images: png, jpg, jpeg, webp, bmp, tiff
- PDFs
- Text files: txt, md, csv, json
- ZIP files containing the above

NOT SUPPORTED (on purpose):
- executables, videos, audio, source code, html, etc.
"""

import pytesseract
from PIL import Image
import json
import sys
import os
import cv2
import numpy as np
from pdf2image import convert_from_path
import tempfile
import zipfile


# -----------------------------
# FILE TYPE DEFINITIONS
# -----------------------------
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
TEXT_EXTS = {".txt", ".md", ".csv", ".json"}
OFFICE_EXTS = {".docx", ".pptx"}  # converted to PDF later


# -----------------------------
# IMAGE PREPROCESSING
# -----------------------------
def preprocess_image(image_path):
    """
    Prepares an image for OCR.
    This removes color noise and improves text clarity.
    """

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Unable to read image")

    # Convert to grayscale (OCR does not need color)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Upscale to help small fonts
    gray = cv2.resize(
        gray,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    # Convert to clean black & white
    _, thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return thresh


# -----------------------------
# QUALITY + GEMINI SIGNALS
# -----------------------------
def assess_quality(text, path, page_count=1):
    """
    Computes OCR confidence + emits metadata for Gemini.

    IMPORTANT:
    This function does NOT "fix" text.
    It only tells downstream AI how careful to be.
    """

    warnings = []
    confidence = 1.0
    text_len = len(text)

    # Very short text is suspicious
    if text_len < 100:
        warnings.append("short_text")
        confidence -= 0.3

    # Measure noise (symbols vs letters)
    non_alpha_ratio = sum(
        1 for c in text if not c.isalnum() and not c.isspace()
    ) / max(text_len, 1)

    if non_alpha_ratio > 0.25:
        warnings.append("low_confidence_text")
        confidence -= 0.4

    # Resolution check (only works for images)
    try:
        img = Image.open(path)
        w, h = img.size
        if w < 800 or h < 800:
            warnings.append("low_resolution")
            confidence -= 0.2
    except:
        # PDFs and text files land here
        pass

    confidence = max(round(confidence, 2), 0.0)

    # ---- Gemini-facing interpretation ----
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
    """
    Runs OCR on a single image file.
    """

    processed = preprocess_image(image_path)
    text = pytesseract.image_to_string(processed).strip()

    if not text:
        return empty_result("image")

    confidence, warnings, ocr_meta = assess_quality(text, image_path, page_count=1)

    return build_result(text, confidence, warnings, ocr_meta)


# -----------------------------
# PDF OCR
# -----------------------------
def run_pdf_ocr(pdf_path):
    """
    Converts PDF pages to images, then OCRs each page.
    """

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
        return empty_result("pdf", page_count)

    confidence, quality_warnings, ocr_meta = assess_quality(
        full_text, pdf_path, page_count
    )

    return build_result(
        full_text,
        confidence,
        list(set(warnings + quality_warnings)),
        ocr_meta
    )


# -----------------------------
# TEXT PASSTHROUGH (NO OCR)
# -----------------------------
def run_text_passthrough(path):
    """
    Used for .txt, .md, .csv, .json files.
    No OCR needed, just read text.
    """

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read().strip()

    if not text:
        return empty_result("text")

    return {
        "schema_version": "1.2",
        "text": text,
        "overall_confidence": 1.0,
        "warnings": [],
        "ocr_meta": {
            "input_type": "text",
            "page_count": 1,
            "noise_level": "low",
            "recommended_llm_mode": "creative",
            "text_density": "high" if len(text) > 1500 else "medium",
            "avg_chars_per_page": len(text)
        }
    }


# -----------------------------
# OFFICE → PDF (STUB)
# -----------------------------
def convert_office_to_pdf(path):
    """
    DOCX / PPTX → PDF conversion.
    Intentionally left as a stub.

    In deployment, use:
    libreoffice --headless --convert-to pdf <file>
    """
    raise NotImplementedError(
        "Office to PDF conversion requires LibreOffice in server environment."
    )


# -----------------------------
# ZIP HANDLING
# -----------------------------
def run_zip(path):
    """
    Extracts ZIP and processes each supported file inside.
    Returns a list of OCR results.
    """

    results = []

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(path, "r") as z:
            z.extractall(tmpdir)

        for root, _, files in os.walk(tmpdir):
            for file in files:
                fpath = os.path.join(root, file)
                try:
                    results.append(dispatch_file(fpath))
                except Exception as e:
                    results.append({
                        "file": file,
                        "error": str(e)
                    })

    return results


# -----------------------------
# DISPATCHER (THE BRAIN)
# -----------------------------
def dispatch_file(path):
    """
    Decides how to process a file based on extension.
    """

    ext = os.path.splitext(path)[1].lower()

    if ext in IMAGE_EXTS:
        return run_image_ocr(path)

    if ext == ".pdf":
        return run_pdf_ocr(path)

    if ext in TEXT_EXTS:
        return run_text_passthrough(path)

    if ext in OFFICE_EXTS:
        pdf_path = convert_office_to_pdf(path)
        return run_pdf_ocr(pdf_path)

    if ext == ".zip":
        return run_zip(path)

    raise ValueError(f"Unsupported file type: {ext}")


# -----------------------------
# HELPERS
# -----------------------------
def empty_result(input_type, page_count=1):
    """
    Standard empty output.
    """

    return {
        "schema_version": "1.2",
        "text": "",
        "overall_confidence": 0.0,
        "warnings": ["no_text_detected"],
        "ocr_meta": {
            "input_type": input_type,
            "page_count": page_count,
            "noise_level": "high",
            "recommended_llm_mode": "strict",
            "text_density": "low",
            "avg_chars_per_page": 0
        }
    }


def build_result(text, confidence, warnings, ocr_meta):
    """
    Standard successful output.
    """

    return {
        "schema_version": "1.2",
        "text": text,
        "overall_confidence": confidence,
        "warnings": warnings,
        "ocr_meta": ocr_meta
    }


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python ocr_local.py <file_path>")
        sys.exit(1)

    path = sys.argv[1]
    output = dispatch_file(path)
    print(json.dumps(output, indent=2))
