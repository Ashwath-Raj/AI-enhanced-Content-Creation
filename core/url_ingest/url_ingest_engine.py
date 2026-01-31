"""
url_ingest_engine.py

Unified URL ingestion for Webpages and YouTube videos.
Handles scraping, cleaning, and extracting text content.
"""

import re
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from urllib.parse import urlparse, parse_qs

# ============================================================
# HELPER: TEXT CLEANING
# ============================================================
def clean_whitespace(text):
    """Collapses multiple spaces/newlines into single ones."""
    if not text:
        return ""
    # Replace whitespace characters with a single space
    return " ".join(text.split())

# ============================================================
# LOGIC: YOUTUBE
# ============================================================
def is_youtube_url(url):
    try:
        domain = urlparse(url).netloc.lower()
        return "youtube.com" in domain or "youtu.be" in domain
    except:
        return False

def get_video_id(url):
    """Parses video ID from youtube.com or youtu.be URLs."""
    try:
        parsed = urlparse(url)
        if "youtu.be" in parsed.netloc:
            return parsed.path[1:] # /VIDEO_ID
        if "youtube.com" in parsed.netloc:
            qs = parse_qs(parsed.query)
            return qs.get("v", [None])[0]
    except:
        pass
    return None

def ingest_youtube(url):
    video_id = get_video_id(url)
    if not video_id:
        return build_result("", 0.0, ["invalid_youtube_url"], "youtube", url)
    
    try:
        # Instantiate the API (v1.2.4+ requires OOP style)
        api = YouTubeTranscriptApi()
        
        # Fetch available transcripts
        transcript_list = api.list(video_id)
        
        transcript = None
        
        # 1. Try finding manually created English transcript
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
        except:
            pass
            
        # 2. If not, try generated English
        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
            except:
                pass
        
        # 3. Fail if no English
        if not transcript:
             return build_result("", 0.0, ["no_english_transcript"], "youtube", url)

        # Fetch the actual data
        data = transcript.fetch()
        
        # Join text parts
        # Note: In this version of the library, fetch() returns objects with .text attribute
        full_text = " ".join([item.text for item in data])
        cleaned_text = clean_whitespace(full_text)
        
        return build_result(cleaned_text, 1.0, [], "youtube", url)

    except (TranscriptsDisabled, NoTranscriptFound, Exception) as e:
        # Just catch everything and return 0.0 confidence as per requirement
        # Spec says "return empty text with warning"
        error_msg = str(e)
        if "TranscriptsDisabled" in error_msg:
            warn = "transcripts_disabled"
        elif "NoTranscriptFound" in error_msg:
            warn = "no_transcript_found"
        else:
            warn = f"youtube_error: {error_msg}"
            
        return build_result("", 0.0, [warn], "youtube", url)

# ============================================================
# LOGIC: WEBPAGE
# ============================================================
def ingest_webpage(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' 
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36'
        }
        # Timeout 10s to prevent hanging
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code >= 400:
            return build_result("", 0.0, [f"http_error_{resp.status_code}"], "web_page", url)
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Remove unwanted tags
        # Removing nav and footer helps reduce boilerplate noise
        for tag in soup(['script', 'style', 'nav', 'footer', 'iframe', 'noscript', 'header', 'aside']):
            tag.decompose()
            
        text = soup.get_text(separator=' ')
        cleaned_text = clean_whitespace(text)
        
        if not cleaned_text:
             return build_result("", 0.0, ["empty_page_content"], "web_page", url)
             
        # Confidence heuristic
        conf = 1.0
        warnings = []
        
        # Very short content might be a blocking modal, captcha, or empty state
        if len(cleaned_text) < 200:
            conf = 0.6
            warnings.append("short_content")
            
        return build_result(cleaned_text, conf, warnings, "web_page", url)
        
    except requests.exceptions.Timeout:
        return build_result("", 0.0, ["connection_timeout"], "web_page", url)
    except requests.exceptions.ConnectionError:
        return build_result("", 0.0, ["connection_error"], "web_page", url)
    except Exception as e:
        return build_result("", 0.0, [f"scrape_error: {str(e)}"], "web_page", url)


# ============================================================
# SHARED BUILDER
# ============================================================
def build_result(text, confidence, warnings, source_type, url):
    
    # Calculate density for metadata
    text_len = len(text)
    if text_len > 5000:
        density = "high"
    elif text_len > 1000:
        density = "medium"
    else:
        density = "low"
        
    # Recommend LLM mode
    # If we have high confidence and good amount of text: creative
    # If confidence is low or warnings exist: strict (hallucination reduction)
    if confidence >= 0.9 and density in ["medium", "high"]:
        llm_mode = "creative"
    elif confidence < 0.8:
        llm_mode = "strict"
    else:
        llm_mode = "normal"
    
    # Simple language detection placeholder
    # In a real app we might use langdetect, but here we assume English per instructions/context
    language = "en" 

    return {
        "schema_version": "1.3",
        "text": text,
        "overall_confidence": round(confidence, 2),
        "warnings": warnings,
        "source_meta": {
            "source_type": source_type,
            "url": url,
            "language": language
        },
        "ingest_meta": {
            "recommended_llm_mode": llm_mode,
            "text_density": density
        }
    }

# ============================================================
# MAIN ENTRY
# ============================================================
def ingest_url(url):
    """
    Main entry point for URL ingestion.
    Dispatches to YouTube or generic Webpage handler.
    """
    if not url:
         return build_result("", 0.0, ["empty_url"], "unknown", "")

    if is_youtube_url(url):
        return ingest_youtube(url)
    else:
        return ingest_webpage(url)
