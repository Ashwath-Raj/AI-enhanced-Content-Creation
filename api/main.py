
import sys
import os
import shutil
import tempfile
import json
from typing import Optional

# Add project root to path so we can import core modules
sys.path.append(os.getcwd())

from fastapi import FastAPI, Request, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

# Import existing engines
# We assume the layout:
# core/ocr/ocr_engine.py -> contains dispatch_file
# core/url_ingest/url_ingest_engine.py -> contains ingest_url
from core.ocr.ocr_engine import dispatch_file
from core.url_ingest.url_ingest_engine import ingest_url

app = FastAPI(title="Unified Ingestion API")

@app.post("/ingest")
async def ingest_endpoint(request: Request):
    """
    Unified ingestion endpoint.
    Accepts:
      1. Multipart file upload (field='file') -> OCR/Document processing
      2. JSON body {"url": "..."} -> Web/YouTube processing
    """
    
    content_type = request.headers.get("content-type", "").lower()
    
    # ----------------------------------------------------
    # CASE 1: JSON Body (URL)
    # ----------------------------------------------------
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
            
        url = body.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="Missing 'url' field in JSON body")
            
        # Run URL ingestion in threadpool to avoid blocking event loop
        try:
            result = await run_in_threadpool(ingest_url, url)
            return result
        except Exception as e:
            # We want to return 500 but with a clear message
            # The engines themselves usually handle errors and return a dict, 
            # but if they raise an unhandled exception, we catch it here.
            # However, looking at the engines, they try to return a result dict with warnings.
            # If a strict crash happens:
            print(f"Server Error during URL ingest: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ----------------------------------------------------
    # CASE 2: Multipart (File)
    # ----------------------------------------------------
    elif "multipart/form-data" in content_type:
        try:
            form = await request.form()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid form data")
            
        upload = form.get("file")
        if not upload:
            raise HTTPException(status_code=400, detail="Missing 'file' field in form data")
            
        # Check for file-like interface (UploadFile has filename and read)
        if not hasattr(upload, "filename") or not hasattr(upload, "read"):
             raise HTTPException(status_code=400, detail="'file' field must be a file upload")

        # Create a temp file to store the upload
        # We MUST preserve the extension because dispatch_file uses it to route logic.
        
        filename = upload.filename or "unknown"
        ext = os.path.splitext(filename)[1]
        
        # Create temp file
        # restart=False so we can open it again if needed, though usually just path is enough
        fd, temp_path = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        
        try:
            # Write uploaded bytes to temp file
            # We use chunks to potentiall handle large files safely
            with open(temp_path, "wb") as f:
                while content := await upload.read(1024 * 1024):
                    f.write(content)
            
            # Process with OCR engine
            # Run in threadpool
            result = await run_in_threadpool(dispatch_file, temp_path)
            
            # Clean up immediately after processing?
            # dispatch_file might return a list of results (zip) or a single dict.
            # In either case, the processing is done.
            return result
            
        except Exception as e:
            print(f"Server Error during File ingest: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # Always clean up the temp file
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    # ----------------------------------------------------
    # CASE 3: Unknown
    # ----------------------------------------------------
    else:
        raise HTTPException(
            status_code=400, 
            detail="Content-Type must be 'application/json' or 'multipart/form-data'"
        )

