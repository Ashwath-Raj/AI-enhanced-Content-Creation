import os
import json
import time
import datetime
import glob
import hashlib
import requests
import html
from dotenv import load_dotenv
import google.generativeai as genai
from pypdf import PdfReader

# Load environment variables
load_dotenv(override=True)

CMS_ROOT = "smart_cms_data"

def check_env_security():
    """Environment and API Key security verification."""
    if not os.path.exists(".env"):
        return False, "❌ .env file missing! Create one based on .env.example"
    
    # Check for placeholder keys
    key = os.getenv("GEMINI_API_KEY")
    if not key or "YOUR_API_KEY" in key or len(key) < 10:
        return False, "⚠️ Invalid or placeholder GEMINI_API_KEY found in .env"
        
    return True, "✅ Security checks passed."

def get_api_key(task_type):
    key_map = {
        "creation": "GEMINI_API_KEY_CREATION",
        "transformation": "GEMINI_API_KEY_TRANSFORMATION",
        "cms": "GEMINI_API_KEY_CMS",
        "personalization": "GEMINI_API_KEY_PERSONALIZATION"
    }
    env_var = key_map.get(task_type)
    key = os.getenv(env_var)
    if not key or "YOUR_API_KEY" in key:
        key = os.getenv("GEMINI_API_KEY")
    return key.strip() if key else None

def call_gemini(prompt, task_type, model_name='gemini-2.5-flash'):
    api_key = get_api_key(task_type)
    if not api_key:
        return f"Error: API Key for '{task_type}' is missing."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"

def generate_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]

def extract_text_from_pdf(file_path):
    try:
        pdf = PdfReader(file_path)
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
        return text
    except Exception as e: return f"Error reading PDF: {e}"

def calculate_reading_time(text):
    words = len(text.split())
    minutes = words / 200
    return f"{minutes:.1f} min"

def sanitize_text(text):
    if text is None: return ""
    return html.escape(str(text))

def get_youtube_transcript(url):
    from youtube_transcript_api import YouTubeTranscriptApi
    try:
        video_id = url.split("v=")[1].split("&")[0]
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript])
    except Exception as e: return f"Error fetching YouTube transcript: {e}"

class IngestionClient:
    BASE_URL = "https://ai-enhanced-content-creation-ocr-api.onrender.com/ingest"
    
    def ingest_file(self, file_name, file_content, file_type):
        try:
            files = {'file': (file_name, file_content, file_type)}
            response = requests.post(self.BASE_URL, files=files, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def ingest_url(self, url):
        try:
            payload = {"url": url}
            response = requests.post(self.BASE_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

class ContentManager:
    LIFECYCLE_STAGES = ["Idea", "Draft", "Review", "Approval", "Publication", "Archival"]
    
    def __init__(self):
        if not os.path.exists(CMS_ROOT):
            os.makedirs(CMS_ROOT)
            
    def _get_path(self, folder, project_id):
        return os.path.join(CMS_ROOT, folder, project_id)

    def create_project(self, title, folder, content, tags=None, extra_meta=None):
        timestamp = int(time.time())
        if not title: title = "Untitled Project"
        clean_title = "".join([c if c.isalnum() else "_" for c in title])[:30]
        project_id = f"{timestamp}_{clean_title}"
        path = self._get_path(folder, project_id)
        
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            
        return self.commit_version(folder, project_id, content, title, tags or [], "Idea", "Initial commit", extra_meta)

    def commit_version(self, folder, project_id, content, title, tags, status, message="Update", extra_meta=None):
        path = self._get_path(folder, project_id)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            
        timestamp = datetime.datetime.now().isoformat()
        content_hash = generate_hash(content + timestamp)
        
        word_count = len(content.split())
        char_count = len(content)
        read_time = calculate_reading_time(content)
        
        version_data = {
            "version_id": content_hash,
            "timestamp": timestamp,
            "title": title,
            "content": content,
            "tags": tags,
            "status": status,
            "message": message,
            "metrics": {
                "word_count": word_count,
                "char_count": char_count,
                "read_time": read_time
            },
            "extra_meta": extra_meta or {}
        }
        
        with open(os.path.join(path, f"v_{content_hash}.json"), "w") as f:
            json.dump(version_data, f, indent=2)
            
        meta = {
            "current_head": content_hash,
            "folder": folder,
            "project_id": project_id,
            "last_modified": timestamp,
            "title": title, 
            "tags": tags,
            "status": status,
            "latest_metrics": version_data['metrics']
        }
        with open(os.path.join(path, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
            
        return project_id

    def get_meta(self, folder, project_id):
        try:
            with open(os.path.join(self._get_path(folder, project_id), "meta.json"), "r") as f:
                return json.load(f)
        except: return None

    def get_history(self, folder, project_id):
        path = self._get_path(folder, project_id)
        files = glob.glob(os.path.join(path, "v_*.json"))
        history = []
        for f in files:
            with open(f, "r") as r:
                history.append(json.load(r))
        return sorted(history, key=lambda x: x['timestamp'], reverse=True)

    def list_all_content(self):
        projects = []
        for folder_path in glob.glob(os.path.join(CMS_ROOT, "*")):
            if os.path.isdir(folder_path):
                folder_name = os.path.basename(folder_path)
                for proj_path in glob.glob(os.path.join(folder_path, "*")):
                    if os.path.isdir(proj_path):
                        proj_id = os.path.basename(proj_path)
                        meta = self.get_meta(folder_name, proj_id)
                        if meta:
                            projects.append(meta)
        return sorted(projects, key=lambda x: x['last_modified'], reverse=True)
    
    def get_folders(self):
        if not os.path.exists(CMS_ROOT): return []
        return [d for d in os.listdir(CMS_ROOT) if os.path.isdir(os.path.join(CMS_ROOT, d))]
