"""
ocr_local.py

Unified document ingestion + OCR service.

WHAT THIS FILE DOES:
- Accepts MANY reasonable file types (image, pdf, text, zip)
- Supports drag-and-drop, multiple files, and folders
- Normalizes everything into ONE JSON output format
- Runs OCR only when needed
- Emits Gemini-aware metadata so LLMs don't hallucinate
- Preserves original file metadata (name, size, path, etc.)
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
from datetime import datetime


# ============================================================
# FILE TYPE DEFINITIONS
# ============================================================
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
TEXT_EXTS  = {".txt", ".md", ".csv", ".json"}
OFFICE_EXTS = {".docx", ".pptx"}  # conversion stub only


# ============================================================
# IMAGE PREPROCESSING
# ============================================================
def preprocess_image(image_path):
    """
    Prepares an image for OCR.
    - Removes color noise
    - Upscales small text
    - Applies binary thresholding

    NOTE:
    This function does NOT attempt to "improve meaning".
    It only improves OCR readability.
    """

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Unable to read image")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Upscale to help OCR with small fonts
    gray = cv2.resize(
        gray,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    # Convert to clean black & white
    _, thresh = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return thresh


# ============================================================
# QUALITY ASSESSMENT + GEMINI SIGNALS
# ============================================================
def assess_quality(text, path, page_count=1):
    """
    Estimates OCR quality and produces Gemini-facing metadata.

    IMPORTANT PHILOSOPHY:
    - OCR never "fixes" text
    - This function only tells downstream AI HOW CAREFUL TO BE
    """

    warnings = []
    confidence = 1.0
    text_len = len(text)

    # Very short text is suspicious
    if text_len < 100:
        warnings.append("short_text")
        confidence -= 0.3

    # Noise detection: symbols vs letters
    non_alpha_ratio = sum(
        1 for c in text if not c.isalnum() and not c.isspace()
    ) / max(text_len, 1)

    if non_alpha_ratio > 0.25:
        warnings.append("low_confidence_text")
        confidence -= 0.4

    # Resolution check (images only)
    try:
        img = Image.open(path)
        w, h = img.size
        if w < 800 or h < 800:
            warnings.append("low_resolution")
            confidence -= 0.2
    except:
        # PDFs / text files land here
        pass

    confidence = max(round(confidence, 2), 0.0)

    # Gemini behavior control
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


# ============================================================
# OCR HANDLERS
# ============================================================
def run_image_ocr(path):
    processed = preprocess_image(path)
    text = pytesseract.image_to_string(processed).strip()

    if not text:
        return empty_result("image")

    conf, warn, meta = assess_quality(text, path, 1)
    return build_result(text, conf, warn, meta)


def run_pdf_ocr(path):
    all_text = []
    warnings = []

    pages = convert_from_path(path, dpi=300)
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

    conf, warn2, meta = assess_quality(full_text, path, page_count)
    return build_result(
        full_text,
        conf,
        list(set(warnings + warn2)),
        meta
    )


def run_text_passthrough(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read().strip()

    if not text:
        return empty_result("text")

    return {
        "schema_version": "1.3",
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


# ============================================================
# OFFICE → PDF (STUB)
# ============================================================
def convert_office_to_pdf(path):
    """
    DOCX / PPTX → PDF conversion.

    Left intentionally unimplemented.
    In production:
        libreoffice --headless --convert-to pdf <file>
    """
    raise NotImplementedError(
        "Office conversion requires LibreOffice in server environment."
    )


# ============================================================
# ZIP HANDLING
# ============================================================
def run_zip(path):
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
                        "file_meta": {
                            "file_name": file
                        },
                        "error": str(e)
                    })

    return results


# ============================================================
# DISPATCHER (THE BRAIN)
# ============================================================
def dispatch_file(path):
    ext = os.path.splitext(path)[1].lower()

    if ext in IMAGE_EXTS:
        return attach_metadata(path, run_image_ocr(path))

    if ext == ".pdf":
        return attach_metadata(path, run_pdf_ocr(path))

    if ext in TEXT_EXTS:
        return attach_metadata(path, run_text_passthrough(path))

    if ext in OFFICE_EXTS:
        pdf_path = convert_office_to_pdf(path)
        return attach_metadata(path, run_pdf_ocr(pdf_path))

    if ext == ".zip":
        return attach_metadata(path, run_zip(path))

    raise ValueError(f"Unsupported file type: {ext}")


# ============================================================
# METADATA + RESULT HELPERS
# ============================================================
def attach_metadata(path, result):
    """
    Attaches file-level metadata WITHOUT touching OCR content.
    """

    meta = {
        "file_name": os.path.basename(path),
        "file_extension": os.path.splitext(path)[1].lower(),
        "file_size_bytes": os.path.getsize(path),
        "source_path": os.path.abspath(path),
        "ingested_at": datetime.utcnow().isoformat() + "Z"
    }

    if isinstance(result, list):
        for r in result:
            r["file_meta"] = meta
        return result

    result["file_meta"] = meta
    return result


def empty_result(input_type, page_count=1):
    return build_result(
        "",
        0.0,
        ["no_text_detected"],
        {
            "input_type": input_type,
            "page_count": page_count,
            "noise_level": "high",
            "recommended_llm_mode": "strict",
            "text_density": "low",
            "avg_chars_per_page": 0
        }
    )


def build_result(text, confidence, warnings, ocr_meta):
    return {
        "schema_version": "1.3",
        "text": text,
        "overall_confidence": confidence,
        "warnings": warnings,
        "ocr_meta": ocr_meta
    }


# ============================================================
# ENTRY POINT (DRAG & DROP FRIENDLY)
# ============================================================
if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Drag & drop files or folders into the terminal.")
        sys.exit(1)

    inputs = sys.argv[1:]
    outputs = []

    for item in inputs:
        if os.path.isdir(item):
            for root, _, files in os.walk(item):
                for f in files:
                    outputs.append(dispatch_file(os.path.join(root, f)))
        else:
            outputs.append(dispatch_file(item))

    print(json.dumps(outputs if len(outputs) > 1 else outputs[0], indent=2))
