====================================================================
 AI-ENHANCED CONTENT CREATION
 Unified OCR + URL Ingestion API
====================================================================

PURPOSE
-------
This project is a unified ingestion layer that converts arbitrary
documents and URLs into clean, LLM-ready text with confidence metadata.

It exists to solve one problem:

  LLMs hallucinate when fed raw PDFs, images, or HTML.

This system ensures:
  - Text is extracted safely
  - Noise is measured
  - Confidence is explicit
  - Downstream AI knows how careful to be


WHAT THIS IS
------------
- Stateless ingestion service
- OCR + URL extraction
- Single API endpoint
- Designed to sit BEFORE Gemini / GPT / Claude

WHAT THIS IS NOT
----------------
- Not a database
- Not a frontend
- Not authentication
- Not an AI model
- Not a summarizer


====================================================================
 ARCHITECTURE
====================================================================

               +-------------------+
               |   USER / CLIENT   |
               +-------------------+
                         |
                         v
               POST /ingest (API)
                         |
        +----------------+----------------+
        |                                 |
        v                                 v
  FILE INGESTION                     URL INGESTION
  (OCR / TEXT)                      (HTML / PAGE)
        |                                 |
        +---------------+-----------------+
                        |
                        v
              NORMALIZED JSON OUTPUT
              + text
              + confidence
              + LLM guidance


====================================================================
 PROJECT STRUCTURE
====================================================================

pROJECT/
│
├── core/
│   ├── ocr/
│   │   └── ocr_engine.py
│   │        - Image OCR
│   │        - PDF OCR
│   │        - Text passthrough
│   │        - Quality analysis
│   │
│   ├── url_ingest/
│   │   └── url_ingest_engine.py
│   │        - Web page ingestion
│   │        - Content extraction
│   │
│   └── contracts/
│        - Reserved for schemas
│
├── api/
│   └── main.py
│        - FastAPI wrapper
│        - /ingest endpoint
│
├── cli/
│        - Reserved (future)
│
├── tests/
│        - Reserved
│
└── venv/
         - Python virtual environment


====================================================================
 SUPPORTED INPUTS
====================================================================

FILES
-----
Images:
  .png .jpg .jpeg .webp .bmp .tiff

Documents:
  .pdf

Text:
  .txt .md .csv .json

Archives:
  .zip (containing supported files)

NOT SUPPORTED (BY DESIGN)
------------------------
  executables
  videos
  audio
  source code
  html uploads


URLS
----
  Any public HTTP/HTTPS webpage


====================================================================
 API
====================================================================

BASE URL
--------
https://ai-enhanced-content-creation-ocr-api.onrender.com


ENDPOINT
--------
POST /ingest


====================================================================
 USING THE API
====================================================================

1) FILE INGESTION
-----------------

Command:
curl -X POST https://ai-enhanced-content-creation-ocr-api.onrender.com/ingest \
     -F "file=@sample.pdf"


2) URL INGESTION
----------------

Command:
curl -X POST https://ai-enhanced-content-creation-ocr-api.onrender.com/ingest \
     -H "Content-Type: application/json" \
     -d '{"url":"https://example.com"}'


====================================================================
 RESPONSE FORMAT
====================================================================

The API returns JSON ONLY.
The structure is NEVER altered.

Example:

{
  "schema_version": "1.3",
  "text": "... extracted content ...",
  "overall_confidence": 0.8,
  "warnings": [],
  "ocr_meta": {
    "input_type": "pdf",
    "page_count": 4,
    "noise_level": "medium",
    "recommended_llm_mode": "normal",
    "text_density": "high",
    "avg_chars_per_page": 1800
  },
  "file_meta": {
    "file_name": "sample.pdf",
    "file_extension": ".pdf",
    "file_size_bytes": 412381,
    "ingested_at": "2026-01-31T09:26:04Z"
  }
}


====================================================================
 HOW GEMINI / LLMS SHOULD USE THIS
====================================================================

DO NOT GUESS.
READ THE METADATA.

recommended_llm_mode:
  creative -> free reasoning allowed
  normal   -> moderate caution
  strict   -> quote only, no inference

noise_level:
  low      -> clean text
  medium   -> OCR artifacts possible
  high     -> unreliable text

overall_confidence:
  > 0.8    -> safe to reason
  0.5-0.8  -> cautious reasoning
  < 0.5    -> do not infer


====================================================================
 ERROR BEHAVIOR
====================================================================

400 BAD REQUEST
  - No file or URL provided
  - Invalid payload

500 SERVER ERROR
  - OCR failure
  - URL extraction failure

Errors are returned as JSON.


====================================================================
 DEPLOYMENT
====================================================================

- Stateless
- No database
- No auth
- Render-compatible
- Runs from master branch

Command:
uvicorn api.main:app --host 0.0.0.0 --port 8000


====================================================================
 FINAL NOTE
====================================================================

This is NOT "just OCR".

This is a SAFETY LAYER for AI systems.

It ensures:
  - Inputs are normalized
  - Noise is measured
  - Hallucinations are reduced
  - Tokens are not wasted

If the LLM lies after this layer,
it is the LLM's fault.

====================================================================
