
import streamlit as st
import os
import glob
import json
import datetime
import time
import hashlib
import io
import difflib
import html
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# --- Dependency Check ---
try:
    import google.generativeai as genai
    import requests
    from bs4 import BeautifulSoup
    from pypdf import PdfReader
    from youtube_transcript_api import YouTubeTranscriptApi
    dependencies_installed = True
except ImportError as e:
    dependencies_installed = False
    missing_module = str(e)

# --- Configuration & Setup ---
st.set_page_config(
    page_title="Content OS v4.0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    /* Premium Look */
    .main { background-color: #f8f9fa; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { color: #111827; font-weight: 700; letter-spacing: -0.025em; }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white; border: none; border-radius: 8px;
        padding: 0.5rem 1.2rem; font-weight: 600;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.2);
    }
    .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.3); }
    
    /* Secondary Button */
    button[kind="secondary"] {
        background: transparent; color: #4b5563; border: 1px solid #d1d5db;
        box-shadow: none;
    }
    
    /* Cards */
    .content-card {
        background: white; border-radius: 12px; padding: 24px;
        border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 16px; transition: border-color 0.2s;
    }
    .content-card:hover { border-color: #6366f1; }
    
    /* Status Tags */
    .badge { padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
    .status-Idea { background-color: #e0f2fe; color: #0369a1; }
    .status-Draft { background-color: #fef9c3; color: #854d0e; }
    .status-Review { background-color: #f3e8ff; color: #6b21a8; }
    .status-Approval { background-color: #cffafe; color: #0e7490; }
    .status-Publication { background-color: #dcfce7; color: #15803d; }
    .status-Archival { background-color: #f3f4f6; color: #374151; }
    
    /* Metadata Box */
    .meta-box {
        background-color: #f9fafb; border-radius: 8px; padding: 12px;
        border: 1px solid #f3f4f6; margin-top: 10px; font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# --- Security Checks ---
def check_security():
    # 1. Check for .gitignore
    if not os.path.exists(".gitignore"):
        st.error("🚨 SECURITY DISASTER: .gitignore is missing! API keys are at risk.")
        st.stop()
    
    # 2. Check if .env is ignored
    with open(".gitignore", "r") as f:
        ignored = f.read()
        if ".env" not in ignored:
            st.error("🚨 SECURITY RISK: .env is not in .gitignore. Your keys might be leaked!")
            st.stop()

check_security()

if not dependencies_installed:
    st.error(f"❌ Missing Dependency: {missing_module}")
    st.warning("Please run: `pip install google-generativeai beautifulsoup4 requests python-dotenv pypdf youtube-transcript-api`")
    st.stop()

# --- Helpers ---
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
        st.error(f"⚠️ API Key for '{task_type}' is missing.")
        return None
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    try:
        return model.generate_content(prompt).text
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def generate_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]

def extract_text_from_pdf(file):
    try:
        pdf = PdfReader(file)
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
        return text
    except Exception as e: return f"Error reading PDF: {e}"

def get_youtube_transcript(url):
    try:
        video_id = url.split("v=")[1].split("&")[0]
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript])
    except Exception as e: return f"Error fetching YouTube transcript: {e}"

def calculate_reading_time(text):
    words = len(text.split())
    minutes = words / 200
    return f"{minutes:.1f} min"



def sanitize_text(text):
    """Sanitize text to prevent XSS when rendering HTML"""
    if text is None: return ""
    return html.escape(str(text))

# --- Ingestion Client ---
class IngestionClient:
    BASE_URL = "https://ai-enhanced-content-creation-ocr-api.onrender.com/ingest"
    
    def ingest_file(self, file_uploader_obj):
        try:
            # Render API expects 'file' in multipart/form-data
            files = {'file': (file_uploader_obj.name, file_uploader_obj.getvalue(), file_uploader_obj.type)}
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

ingest_client = IngestionClient()

# --- Smart CMS with Git-Like Versioning ---
CMS_ROOT = "smart_cms_data"

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
            os.makedirs(path)
            
        # Initial Commit
        self.commit_version(folder, project_id, content, title, tags or [], "Idea", "Initial commit", extra_meta)
        return project_id

    def commit_version(self, folder, project_id, content, title, tags, status, message="Update", extra_meta=None):
        path = self._get_path(folder, project_id)
        timestamp = datetime.datetime.now().isoformat()
        content_hash = generate_hash(content + timestamp)
        
        # Enhanced Metadata
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
        
        # Save Version File
        with open(os.path.join(path, f"v_{content_hash}.json"), "w") as f:
            json.dump(version_data, f, indent=2)
            
        # Update HEAD (Meta file)
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
            
        return content_hash

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
        return [d for d in os.listdir(CMS_ROOT) if os.path.isdir(os.path.join(CMS_ROOT, d))]

cms = ContentManager()

# --- PERSONALIZATION MONITORING ---
class UserBehaviorTracker:
    def __init__(self):
        if 'user_prefs' not in st.session_state:
            st.session_state['user_prefs'] = {
                "interactions": 0,
                "liked_tones": [],
                "preferred_length": "Medium",
                "session_start": time.time(),
                "clicked_projects": set(),
                "engagement_metrics": { # Simulated External Engagement
                    "total_likes": 0, 
                    "top_performing_tone": None 
                }
            }
    
    def update_engagement(self, likes, tone):
        # update fake engagement model
        self.session_state['user_prefs']['engagement_metrics']['total_likes'] += likes
        if likes > 50: # Threshold for "Good" content
             self.session_state['user_prefs']['liked_tones'].append(tone)
    
    def log_interaction(self, interaction_type, details=None):
        st.session_state['user_prefs']['interactions'] += 1
        if interaction_type == "click_project":
            st.session_state['user_prefs']['clicked_projects'].add(details)
            
    def get_metrics(self):
        duration = time.time() - st.session_state['user_prefs']['session_start']
        return {
            "session_duration_min": round(duration / 60, 2),
            "interactions": st.session_state['user_prefs']['interactions'],
            "projects_viewed": len(st.session_state['user_prefs']['clicked_projects'])
        }
    
    def update_preference(self, category, value, positive=True):
        if category == "tone":
            if positive:
                st.session_state['user_prefs']['liked_tones'].append(value)
            elif value in st.session_state['user_prefs']['liked_tones']:
                st.session_state['user_prefs']['liked_tones'].remove(value)

tracker = UserBehaviorTracker()

# --- UI STATE MANGEMENT ---
if 'nav_engine' not in st.session_state: st.session_state['nav_engine'] = 'CMS'
if 'active_project' not in st.session_state: st.session_state['active_project'] = None
if 'generated_content' not in st.session_state: st.session_state['generated_content'] = ""

# --- SIDEBAR NAV ---
with st.sidebar:
    st.title("⚡ Content OS")
    st.markdown("---")
    engine = st.radio("Core Engine", ["CMS Library", "Creation Engine", "Transformation Engine", "Personalization Engine"], index=1)
    st.markdown("---")
    
    with st.expander("📂 Folder Manager", expanded=False):
        new_folder = st.text_input("New Folder", placeholder="Name...")
        if st.button("Create") and new_folder:
            os.makedirs(os.path.join(CMS_ROOT, new_folder), exist_ok=True)
            st.success(f"Created {new_folder}")
            time.sleep(0.5)
            st.rerun()
        
        folders = cms.get_folders()
        if folders:
            st.markdown("### Existing Folders")
            st.caption(", ".join(folders))
            
    with st.expander("📤 Import File to CMS", expanded=False):
        imp_file = st.file_uploader("Upload Document/Image", type=['txt', 'md', 'pdf', 'png', 'jpg', 'jpeg'])
        imp_folder = st.selectbox("Target Folder", folders or ["General"])
        if imp_file:
            imp_title = st.text_input("Project Title", os.path.splitext(imp_file.name)[0])
            if st.button("Import & Create"):
                text = ""
                extra_meta = {}
                
                # Try API Ingestion first for PDFs/Images
                if imp_file.type in ['application/pdf', 'image/png', 'image/jpeg', 'image/webp']:
                    with st.spinner("Analyzing document via OCR API..."):
                        api_res = ingest_client.ingest_file(imp_file)
                        if "text" in api_res:
                            text = api_res['text']
                            extra_meta = api_res.get('ocr_meta', {})
                            extra_meta['confidence'] = api_res.get('overall_confidence', 0)
                        else:
                            st.warning(f"API Ingestion failed, falling back to local: {api_res.get('error')}")
                
                # Fallback / Text files
                if not text:
                    if imp_file.type == "application/pdf":
                        text = extract_text_from_pdf(imp_file)
                    else:
                        try:
                            text = imp_file.getvalue().decode("utf-8")
                        except:
                            text = "Error: Could not decode text."
                
                if text:
                    cms.create_project(imp_title, imp_folder, text, tags=["Imported", "Ingestion"], extra_meta=extra_meta)
                    st.success(f"Imported '{imp_title}'!")
                    if extra_meta.get('confidence'):
                        st.caption(f"Confidence: {extra_meta['confidence']}")
                    time.sleep(1)
                    st.rerun()

# --- WEB BOILERPLATE GENERATOR ---
def get_web_boilerplate(title, content):
    """
    Generates a standalone HTML file for GitHub Pages deployment.
    Contains a prompt for AI enhancement.
    """
    html_template = f"""<!-- 
PROMPT TO ENHANCE THIS FILE:
"You are an expert web developer. Refine this HTML file to be a stunning, responsive, and SEO-optimized blog post page. 
Current Stack: HTML5, CSS3, Vanilla JS, Marked.js for Markdown rendering.
Requirements:
1. Improve the Typography using Google Fonts (Inter/Merriweather).
2. Add a Dark/Light mode toggle.
3. Enhance the CSS for a 'Medium-like' reading experience (max-width, line-height, spacing).
4. Make specific styles for code blocks, blockquotes, and headers.
5. Ensure it is ready for GitHub Pages (relative paths, meta tags).
6. Keep it contained in a single file if possible."
-->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="Generated by Content OS">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        img {{ max-width: 100%; height: auto; border-radius: 8px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #ccc; margin: 0; padding-left: 16px; color: #666; }}
        h1 {{ font-size: 2.5em; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .meta {{ color: #777; font-size: 0.9em; margin-bottom: 30px; }}
        #content {{ margin-top: 40px; }}
    </style>
</head>
<body>
    <div id="content">
        <!-- Content will be rendered here -->
    </div>

    <!-- DATA HIDDEN IN SCRIPT FOR JS TO PARSE -->
    <script id="raw-markdown" type="text/markdown">
{content}
    </script>

    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const raw = document.getElementById('raw-markdown').textContent;
            document.getElementById('content').innerHTML = marked.parse(raw);
        }});
    </script>
</body>
</html>
"""
    return html_template

# ================= CMS LIBRARY VIEW =================
if engine == "CMS Library":
    st.header("📂 Content Library & Smart CMS")
    
    # Filter
    search_col, sort_col = st.columns([3, 1])
    search_q = search_col.text_input("🔍 Semantic Search (Topic/Tags)", placeholder="Search by meaning...")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Projects")
        projects = cms.list_all_content()
        for p in projects:
            if search_q.lower() in p['title'].lower() or search_q.lower() in str(p['tags']).lower():
                with st.container():
                    st.markdown(f"""
                    <div class="content-card">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <h4 style="margin:0">{sanitize_text(p['title'])}</h4>
                            <span class="badge status-{sanitize_text(p['status'])}">{sanitize_text(p['status'])}</span>
                        </div>
                        <small style="color:#6b7280; display:block; margin-top:5px;">
                            📁 {sanitize_text(p['folder'])} • 🕒 {sanitize_text(p['last_modified'][:10])}
                        </small>
                        <div style="margin-top:8px;">
                            <span style="font-size:0.8em; background:#eee; padding:2px 6px; border-radius:4px;">Drafts: {p.get('latest_metrics', {}).get('word_count', 0)} words</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("Edit Project", key=f"btn_{p['project_id']}", use_container_width=True):
                        st.session_state['active_project'] = p
                        st.rerun()

    with col2:
        if st.session_state['active_project']:
            active_meta = st.session_state['active_project']
            folder = active_meta['folder']
            pid = active_meta['project_id']
            
            history = cms.get_history(folder, pid)
            # Ensure we have data
            if not history:
                st.error("No history found for this project.")
            else:
                st.subheader(f"✏️ Editor: {active_meta['title']}")
                
                # --- LIFECYCLE & VERSION BAR ---
                c1, c2, c3 = st.columns([1, 2, 1])
                
                # Version Dropdown (The key requested feature)
                version_options = {f"v.{v['timestamp'][11:16]} ({v['version_id'][:6]})": i for i, v in enumerate(history)}
                selected_v_idx = c1.selectbox("Version History", options=list(version_options.keys()), index=0)
                view_version = history[version_options[selected_v_idx]]
                
                # Status
                new_status = c3.selectbox("Status", ContentManager.LIFECYCLE_STAGES, index=ContentManager.LIFECYCLE_STAGES.index(view_version['status']))
                
                # --- METADATA PANEL (New Feature) ---
                st.markdown(f"""
                <div class="meta-box">
                    <b>📊 Metadata</b><br>
                    Words: {view_version.get('metrics', {}).get('word_count', 0)} | 
                    Chars: {view_version.get('metrics', {}).get('char_count', 0)} | 
                    Reading Time: {view_version.get('metrics', {}).get('read_time', '0 min')} <br>
                    <i>Generated Info: {view_version.get('extra_meta', {}).get('mode', 'Manual Edit')}</i>
                </div>
                """, unsafe_allow_html=True)
                
                # --- DIFF CHECKER ---
                with st.expander("🔍 Compare Versions"):
                    compare_idx = st.selectbox("Compare against:", ["None"] + list(version_options.keys()), index=0)
                    if compare_idx != "None":
                        comp_v = history[version_options[compare_idx]]
                        diff = difflib.unified_diff(
                            comp_v['content'].splitlines(),
                            view_version['content'].splitlines(),
                            fromfile=f"Version {comp_v['version_id'][:6]}",
                            tofile=f"Version {view_version['version_id'][:6]}",
                            lineterm=''
                        )
                        st.code("\n".join(diff), language="diff")

                # --- IMPORT EXTERNAL ---
                with st.expander("📤 Import / Replace Content"):
                    uploaded_import = st.file_uploader("Upload File to Replace Current Content", type=['txt', 'md', 'json'])
                    if uploaded_import:
                        stringio = io.StringIO(uploaded_import.getvalue().decode("utf-8"))
                        view_version['content'] = stringio.read()
                        st.info("Content loaded from file. Review below before committing.")

                # --- EDITOR AREA ---
                edit_content = st.text_area("", view_version['content'], height=600, label_visibility="collapsed")
                
                # --- FOOTER ACTIONS ---
                fc1, fc2, fc3 = st.columns([2, 2, 1])
                edit_tags = fc1.text_input("Tags", ", ".join(view_version.get('tags', [])))
                commit_msg = fc2.text_input("Commit Message", placeholder="Reason for change...")
                
                if fc3.button("💾 Commit", use_container_width=True):
                    tag_list = [t.strip() for t in edit_tags.split(",") if t.strip()]
                    cms.commit_version(folder, pid, edit_content, active_meta['title'], tag_list, new_status, commit_msg or "Update", extra_meta=view_version.get('extra_meta', {}))
                    st.toast("Saved successfully!", icon="✅")
                    time.sleep(1)
                    st.rerun()
                
                # --- EXPORT ---
                st.markdown("### 📤 Export")
                ec1, ec2, ec3 = st.columns(3)
                ec1.download_button("📥 Markdown", edit_content, file_name=f"{active_meta['title']}.md")
                ec2.download_button("🌍 Website (HTML)", get_web_boilerplate(active_meta['title'], edit_content), file_name="index.html", mime="text/html")
                with ec3:
                     st.caption("💡 The HTML file contains a prompt to further enhance it using AI.")

# ================= CREATION ENGINE =================
elif engine == "Creation Engine":
    st.header("🎨 AI Content Creation Engine")
    
    with st.container():
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        # --- INPUTS ---
        with col1:
            st.subheader("1. Source & Mode")
            mode = st.selectbox("Content Mode", 
                ["Blog Post", "Social Media Post", "Video Script", "Newsletter", "Study Notes", "Marketing Copy", "Technical Documentation"])
            
            src_type = st.radio("Input Source", ["Raw Idea", "Existing Project", "Paste Text", "Document/Image Upload", "YouTube Video", "URL"])
            
            input_context = ""
            api_meta_data = None
            
            if src_type == "Raw Idea":
                input_context = st.text_area("Ideas / Topics", height=150)
            elif src_type == "Existing Project":
                all_projs = cms.list_all_content()
                if not all_projs:
                    st.warning("No existing projects found.")
                else:
                    proj_opts = {p['title']: p for p in all_projs}
                    selected_exist = st.selectbox("Select Project", list(proj_opts.keys()))
                    if selected_exist:
                        p_meta = proj_opts[selected_exist]
                        # Get latest version content
                        latest_content = cms.get_history(p_meta['folder'], p_meta['project_id'])[0]['content']
                        st.text_area("Preview", latest_content[:500]+"...", height=100, disabled=True)
                        input_context = latest_content
            
            elif src_type == "Paste Text":
                input_context = st.text_area("Paste Content", height=150)
            elif src_type == "Document/Image Upload":
                f = st.file_uploader("Upload (PDF, Images, Text)", type=["pdf", "png", "jpg", "jpeg", "webp", "txt", "md"])
                if f: 
                    # Use API if possible
                    if f.type in ['application/pdf', 'image/png', 'image/jpeg', 'image/webp']:
                         with st.spinner("Processing with Ingestion API..."):
                             res = ingest_client.ingest_file(f)
                             if "text" in res:
                                 input_context = res['text']
                                 api_meta_data = res.get('ocr_meta', {})
                                 st.success(f"Ingested! Confidence: {res.get('overall_confidence')}")
                             else:
                                 st.error(f"API Error: {res.get('error')}")
                                 # Fallback logic could go here if user wants, but API is preferred
                                 if f.type == "application/pdf":
                                     st.info("Attempting local PDF fallback...")
                                     input_context = extract_text_from_pdf(f)
                    else:
                        # Simple text read
                        input_context = f.getvalue().decode("utf-8")

            elif src_type == "YouTube Video":
                 yt_url = st.text_input("YouTube URL")
                 if yt_url: 
                     with st.spinner("Fetching Transcript..."):
                        input_context = get_youtube_transcript(yt_url)
                        if "Error" in input_context: st.error(input_context)
                        else: st.success("Transcript loaded!")
                        
            elif src_type == "URL":
                u = st.text_input("URL")
                if u:
                    with st.spinner("Ingesting URL..."):
                        # Try API first
                        res = ingest_client.ingest_url(u)
                        if "text" in res:
                             input_context = res['text']
                             api_meta_data = res.get('ocr_meta', {})
                             st.success(f"Page Ingested. Noise Level: {api_meta_data.get('noise_level', 'Unknown')}")
                        else:
                            st.warning(f"Ingestion API failed ({res.get('error')}). Using basic scraper.")
                            try: input_context = BeautifulSoup(requests.get(u).content, 'html.parser').get_text()[:5000]
                            except: st.error("Bad URL - Local scrape failed too.")

        # --- CONTROLS ---
        with col2:
            st.subheader("2. Generation Controls")
            audience = st.text_input("Target Audience", "General Tech")
            
            c_tone, c_len = st.columns(2)
            tone = c_tone.select_slider("Tone", ["Informal", "Casual", "Professional", "Academic", "Expert"])
            length = c_len.select_slider("Length", ["Short", "Medium", "Long", "Deep Dive"])
            
            depth = st.select_slider("Explanation Depth", ["Basic", "Intermediate", "Advanced", "Expert"])
            platform = st.selectbox("Platform Format", ["Generic", "LinkedIn", "Twitter/X", "Medium", "Substack", "GitHub README"])
            
            with st.expander("Advanced Options"):
                adv_ab = st.checkbox("Generate A/B Variants")
                adv_human = st.checkbox("Human-like Rewriting")
                adv_analogy = st.checkbox("Use Analogies")
            
            save_folder = st.selectbox("Save to Folder", cms.get_folders() or ["General"])

        if st.button("✨ Generate Content", use_container_width=True):
            if not input_context:
                st.error("Please provide valid input source.")
            else:
                with st.spinner("Compiling high-quality content..."):
                    prompt = f"""
                    ACT AS: Expert Content Creator.
                    TASK: Write a {mode}.
                    SOURCE MATERIAL: {input_context[:20000]}
                    
                    TARGET AUDIENCE: {audience}
                    TONE: {tone}
                    LENGTH: {length}
                    DEPTH: {depth}
                    PLATFORM: {platform}
                    
                    ADVANCED INSTRUCTIONS:
                    - { "Create 2 distinct variants (Option A and Option B)" if adv_ab else "Single high-quality version" }
                    - { "Use natural, human-like phrasing (avoid AI cliches)" if adv_human else "" }
                    - { "Explain complex concepts using simple analogies" if adv_analogy else "" }
                    """
                    
                    result = call_gemini(prompt, "creation")
                    if result:
                        st.session_state['generated_content'] = result
                        
                        # Auto-Tagging
                        tags = ["AI-Gen", mode, platform]
                        if adv_ab: tags.append("A/B Testing")
                        
                        # Store gen params in meta
                        gen_meta = {
                            "mode": mode,
                            "source_type": src_type,
                            "tone": tone,
                            "platform": platform
                        }
                        
                        # Save
                        title = f"{mode}: {audience[:15]}... ({datetime.datetime.now().strftime('%H:%M')})"
                        if save_folder == "General" and not os.path.exists(os.path.join(CMS_ROOT, "General")):
                            os.makedirs(os.path.join(CMS_ROOT, "General"))
                        
                        cms.create_project(title, save_folder, result, tags, extra_meta=gen_meta)
                        st.success(f"Generated & Saved to '{save_folder}'!")

    if st.session_state['generated_content']:
        st.markdown("### Result")
        st.markdown(st.session_state['generated_content'])

# ================= TRANSFORMATION ENGINE =================
elif engine == "Transformation Engine":
    st.header("🔄 Content Transformation Engine")
    
    projects = cms.list_all_content()
    opts = {p['title']: p for p in projects}
    sel_proj = st.selectbox("Select Content to Transform", list(opts.keys()) if opts else [])
    
    if sel_proj:
        meta = opts[sel_proj]
        current = cms.get_history(meta['folder'], meta['project_id'])[0]['content']
        st.text_area("Source", current, height=150, disabled=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("One-to-Many Conversion")
            trans_mode = st.selectbox("Convert To", 
                ["Social Media Thread", "Blog Post from Video/Notes", "Quiz/Flashcards", "Executive Summary"])
                
        with col2:
            st.subheader("Semantic Refinement")
            sem_mode = st.selectbox("Refinement Type", 
                ["Simplify (EL15)", "Expand/Elaborate", "Reframe (New Perspective)", "Counter-Argument Gen", "Tone Adjustment"])
        
        if st.button("🚀 Run Transformation"):
            with st.spinner("Transforming..."):
                prompt = f"""
                TASK: Content Transformation
                SOURCE: {current[:15000]}
                
                PRIMARY GOAL: Convert to {trans_mode}
                SECONDARY REFINEMENT: {sem_mode}
                
                Keep the core meaning but adapt strictly to the new format.
                """
                res = call_gemini(prompt, "transformation")
                st.session_state['transform_result'] = res
    
    if 'transform_result' in st.session_state and st.session_state['transform_result']:
        st.markdown("### Transformation Result")
        st.markdown(st.session_state['transform_result'])
        
        if st.button("💾 Save as New Version to Project History"):
            with st.spinner("Saving..."):
                # Save as new version
                meta = opts[sel_proj]
                # Inherit tags
                tags = meta.get('tags', []) + [trans_mode, "Transformed"]
                
                cms.commit_version(
                    folder=meta['folder'],
                    project_id=meta['project_id'],
                    content=st.session_state['transform_result'],
                    title=meta['title'],
                    tags=tags,
                    status="Draft",
                    message=f"Transformed to {trans_mode} ({sem_mode})",
                    extra_meta={"transformation_type": trans_mode}
                )
                st.success(f"Saved to project '{meta['title']}' history!")

# ================= PERSONALIZATION ENGINE =================
elif engine == "Personalization Engine":
    st.header("🧠 Personalization Engine")
    
    # 1. User Behavior Modeling
    with st.expander("📊 User Behavior & Modeling", expanded=True):
        metrics = tracker.get_metrics()
        bmc1, bmc2, bmc3 = st.columns(3)
        bmc1.metric("Engagement Duration", f"{metrics['session_duration_min']} min")
        bmc2.metric("Interaction Count", metrics['interactions'])
        bmc3.metric("Projects Engaged", metrics['projects_viewed'])
        
        st.caption("Based on your current session patterns, we are building a preference model.")
        
        # Simulated 'Reading Behavior' visualization
        st.progress(min(metrics['interactions'] * 5, 100), text="Engagement Score")

    st.markdown("---")

    # 2. Dynamic Personalization Workspace
    st.subheader("🎯 Content Personalization & Smart Editor")
    
    # Select Project (CSM File)
    all_projects = cms.list_all_content()
    proj_map = {p['title']: p for p in all_projects}
    
    col_sel, col_act = st.columns([1, 2])
    
    with col_sel:
        st.markdown("#### Select Source (CSM)")
        selected_p_title = st.selectbox("Choose Project", list(proj_map.keys()), index=0 if list(proj_map.keys()) else None)
        
        if selected_p_title:
            p_data = proj_map[selected_p_title]
            tracker.log_interaction("click_project", selected_p_title)
            
            # --- AUDIENCE ENGAGEMENT SIMULATOR (New Feature) ---
            with st.expander("📈 Audience Engagement Data", expanded=False):
                st.caption("Simulate how this content performed (Mock Data)")
                sim_likes = st.number_input("Likes/Reactions", min_value=0, step=10, key=f"likes_{p_data['project_id']}")
                sim_comments = st.number_input("Comments", min_value=0, key=f"comm_{p_data['project_id']}")
                
                if st.button("Update Engagement Stats", key=f"upd_{p_data['project_id']}"):
                     # Update metadata with this 'fake' engagement
                     current_ver = cms.get_history(p_data['folder'], p_data['project_id'])[0]
                     extra = current_ver.get('extra_meta', {})
                     extra['engagement'] = {"likes": sim_likes, "comments": sim_comments}
                     
                     cms.commit_version(
                        p_data['folder'], p_data['project_id'], 
                        current_ver['content'], 
                        p_data['title'], 
                        p_data['tags'], 
                        current_ver['status'], 
                        "Updated Engagement Stats", 
                        extra_meta=extra
                     )
                     # Feed into learning model
                     tracker.update_preference("tone", extra.get('tone', 'Neutral'), positive=sim_likes > 20)
                     st.toast("Engagement Data Recorded! AI will learn from this.")

            # 3. Learning Feedback Loop Display
            st.info(f"Detected Tone Preference: {max(set(st.session_state['user_prefs']['liked_tones']), key=st.session_state['user_prefs']['liked_tones'].count) if st.session_state['user_prefs']['liked_tones'] else 'Neutral'}")

            st.markdown("#### ⚡ Quick Actions")
            if st.button("Summarize for Me"):
                with st.spinner("Personalizing summary..."):
                    # Get Engagement Context
                    hist = cms.get_history(p_data['folder'], p_data['project_id'])[0]
                    eng_context = hist.get('extra_meta', {}).get('engagement', "No data")
                    
                    # Dynamic Personalization
                    prompt = f"""
                    Summarize this content.
                    USER PREFERENCES: {st.session_state['user_prefs']}
                    PAST ENGAGEMENT ON THIS POST: {eng_context}
                    
                    Identify why this post might have performed well/poorly based on the engagement metrics provided.
                    Content: {hist['content'][:5000]}
                    """
                    summary = call_gemini(prompt, "personalization")
                    st.session_state['pers_output'] = summary

            if st.button("Adapt Tone to My Style"):
                with st.spinner("Adapting tone..."):
                    prompt = f"Rewrite this intro to match a professional but engaging tone (User Preference Model). Content: {cms.get_history(p_data['folder'], p_data['project_id'])[0]['content'][:1000]}"
                    adaptation = call_gemini(prompt, "personalization")
                    st.session_state['pers_output'] = adaptation

    with col_act:
        if selected_p_title:
            # CSM Editor Section (Working on previous CSM file)
            st.markdown(f"### 📝 Smart Editor: {selected_p_title}")
            
            # Load Content
            current_ver = cms.get_history(p_data['folder'], p_data['project_id'])[0]
            current_text = current_ver['content']
            
            # AI Assist Input
            ai_instruction = st.text_input("🤖 Ask AI to edit (e.g., 'Make the second paragraph funnier')", key="ai_edit_input")
            
            if st.button("Run AI Edit"):
                if ai_instruction:
                    with st.spinner("AI is editing..."):
                        edit_prompt = f"""
                        TASK: Edit the following text based on the user instruction.
                        INSTRUCTION: {ai_instruction}
                        TEXT TO EDIT:
                        {current_text}
                        
                        RETURN ONLY THE UPDATED TEXT.
                        """
                        edited_text = call_gemini(edit_prompt, "personalization")
                        if edited_text:
                            current_text = edited_text
                            st.session_state[f'edit_buffer_{p_data["project_id"]}'] = edited_text
                            st.success("AI Edit Applied! Review below.")
            
            # Editor Text Area
            # distinct key to allow manual override
            initial_val = st.session_state.get(f'edit_buffer_{p_data["project_id"]}', current_text)
            new_content = st.text_area("Edit Content", value=initial_val, height=500)
            
            # Save Controls
            if st.button("💾 Save Changes to CSM"):
                cms.commit_version(p_data['folder'], p_data['project_id'], new_content, p_data['title'], p_data['tags'], "Draft", "Personalized/Smart Edit")
                st.toast("Changes Saved!")
                tracker.log_interaction("save_edit")
                time.sleep(1)
                st.rerun()

            # Feedback Loop (Learning)
            if 'pers_output' in st.session_state:
                 st.markdown("---")
                 st.markdown("#### AI Suggestion / Output")
                 st.info(st.session_state['pers_output'])
                 
                 fb_col1, fb_col2 = st.columns(2)
                 if fb_col1.button("👍 Helpful"):
                     tracker.update_preference("tone", "Professional", True) # Simplified model update
                     st.toast("Feedback recorded: Preference updated.")
                 if fb_col2.button("👎 Not Helpful"):
                     tracker.update_preference("tone", "Professional", False)
                     st.toast("Feedback recorded: Adjustment noted.")
