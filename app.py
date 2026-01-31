
import streamlit as st
import os
import glob
import json
import datetime
import time
import hashlib
import io
import difflib
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
        # Clean ID generation
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

# --- UI STATE MANGEMENT ---
if 'nav_engine' not in st.session_state: st.session_state['nav_engine'] = 'CMS'
if 'active_project' not in st.session_state: st.session_state['active_project'] = None
if 'generated_content' not in st.session_state: st.session_state['generated_content'] = ""

# --- SIDEBAR NAV ---
with st.sidebar:
    st.title("⚡ Content OS")
    st.markdown("---")
    engine = st.radio("Core Engine", ["CMS Library", "Creation Engine", "Transformation Engine"], index=0)
    st.markdown("---")
    
    with st.expander("� Folder Manager", expanded=True):
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
                            <h4 style="margin:0">{p['title']}</h4>
                            <span class="badge status-{p['status']}">{p['status']}</span>
                        </div>
                        <small style="color:#6b7280; display:block; margin-top:5px;">
                            📁 {p['folder']} • 🕒 {p['last_modified'][:10]}
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
                    Words: {view_version['metrics'].get('word_count', 0)} | 
                    Chars: {view_version['metrics'].get('char_count', 0)} | 
                    Reading Time: {view_version['metrics'].get('read_time', '0 min')} <br>
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
                st.download_button("📥 Export Markdown", edit_content, file_name=f"{active_meta['title']}.md")

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
            
            src_type = st.radio("Input Source", ["Raw Idea", "Paste Text", "PDF Upload", "YouTube Video", "URL"])
            
            input_context = ""
            if src_type == "Raw Idea":
                input_context = st.text_area("Ideas / Topics", height=150)
            elif src_type == "Paste Text":
                input_context = st.text_area("Paste Content", height=150)
            elif src_type == "PDF Upload":
                f = st.file_uploader("PDF Transcript", type=["pdf"])
                if f: input_context = extract_text_from_pdf(f)
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
                    try: input_context = BeautifulSoup(requests.get(u).content, 'html.parser').get_text()[:5000]
                    except: st.error("Bad URL")

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
                st.markdown(res)
