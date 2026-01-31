
import streamlit as st
import os
import glob
import json
import datetime
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

try:
    import google.generativeai as genai
    dependencies_installed = True
except ImportError as e:
    dependencies_installed = False
    missing_module = str(e)

# --- Configuration & Setup ---
st.set_page_config(
    page_title="Content OS v2.0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; color: #1e1e1e; }
    .stButton>button {
        background: linear-gradient(45deg, #6b4cff, #9072ff);
        color: white; border: none; border-radius: 8px;
        padding: 0.5rem 1.5rem; font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(107, 76, 255, 0.2); }
    .card {
        background-color: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px;
        border-left: 4px solid #6b4cff;
    }
    .status-badge {
        padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold;
    }
    .status-published { background-color: #d4edda; color: #155724; }
    .status-draft { background-color: #fff3cd; color: #856404; }
</style>
""", unsafe_allow_html=True)

# --- Dependency Check ---
if not dependencies_installed:
    st.error(f"❌ Missing Dependency: {missing_module}")
    st.stop()

# --- Helper Functions ---
def get_api_key(task_type):
    """Retrieve task-specific API key, falling back to valid defaults if needed."""
    key_map = {
        "creation": "GEMINI_API_KEY_CREATION",
        "transformation": "GEMINI_API_KEY_TRANSFORMATION",
        "cms": "GEMINI_API_KEY_CMS",
        "personalization": "GEMINI_API_KEY_PERSONALIZATION"
    }
    env_var = key_map.get(task_type)
    key = os.getenv(env_var)
    if not key or "YOUR_API_KEY" in key: # Fallback to main key if specific is missing/default
        key = os.getenv("GEMINI_API_KEY")
    return key.strip() if key else None

def call_gemini(prompt, task_type, model_name='gemini-2.5-flash'):
    api_key = get_api_key(task_type)
    if not api_key:
        st.error(f"⚠️ API Key for '{task_type}' is missing in .env")
        return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"AI Error ({task_type}): {e}")
        return None

# --- CMS System (File-based) ---
CMS_DIR = "cms_data"
if not os.path.exists(CMS_DIR):
    os.makedirs(CMS_DIR)

class CMS:
    @staticmethod
    def save_content(title, content, tags, status="draft", version=1, parent_id=None):
        timestamp = datetime.datetime.now().isoformat()
        file_id = parent_id if parent_id else f"{int(time.time())}"
        
        # Structure
        data = {
            "id": file_id,
            "title": title,
            "content": content,
            "tags": tags,
            "status": status,
            "version": version,
            "timestamp": timestamp
        }
        
        # Save to JSON file
        filename = f"{CMS_DIR}/{file_id}_v{version}.json"
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        return filename

    @staticmethod
    def list_content():
        files = glob.glob(f"{CMS_DIR}/*.json")
        content_list = []
        for f in files:
            with open(f, "r") as r:
                try:
                    content_list.append(json.load(r))
                except: pass
        # Sort by timestamp desc
        return sorted(content_list, key=lambda x: x['timestamp'], reverse=True)

    @staticmethod
    def get_versions(file_id):
        all_content = CMS.list_content()
        return [c for c in all_content if c['id'] == file_id]

# --- UI Layout ---
st.title("⚡ Content Operating System 2.0")

# Navigation
app_mode = st.sidebar.radio("Engine Select", 
    ["🎨 Creation Engine", "🔄 Transformation Engine", "📂 Smart CMS", "👤 Personalization Engine"])

st.sidebar.markdown("---")
# Global Settings in Sidebar
with st.sidebar.expander("⚙️ System Settings"):
    st.info(f"Creation Key: {'✅' if get_api_key('creation') else '❌'}")
    st.info(f"Transform Key: {'✅' if get_api_key('transformation') else '❌'}")
    st.info(f"CMS Key: {'✅' if get_api_key('cms') else '❌'}")
    st.info(f"Persona Key: {'✅' if get_api_key('personalization') else '❌'}")

# --- 1. Creation Engine ---
if "Creation" in app_mode:
    st.header("🎨 AI Content Creation Engine")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Controls")
        content_type = st.selectbox("Content Type", 
            ["Blog Post", "Social Media Thread", "Video Script", "Newsletter", "Marketing Copy", "Technical Docs"])
        target_audience = st.text_input("Target Audience", "General Tech Enthusiasts")
        tone = st.select_slider("Tone", options=["Formal", "Professional", "Casual", "Humorous", "Viral"], value="Professional")
        length = st.select_slider("Length", options=["Short", "Medium", "Long", "Deep Dive"], value="Medium")
        platform = st.selectbox("Platform", ["LinkedIn", "Twitter/X", "Medium", "YouTube", "Internal Wiki"])
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        topic = st.text_area("Topic / Concept / Raw Ideas", height=150, placeholder="E.g., The future of AI agents in software engineering...")
        
        advanced_opts = st.expander("Advanced Generation Options")
        with advanced_opts:
            include_analogy = st.checkbox("Include Analogies")
            ab_testing = st.checkbox("Generate A/B Variants")
        
        if st.button("✨ Generate Content"):
            with st.spinner("Crafting content..."):
                prompt = f"""
                Act as an expert content creator.
                TASK: Write a {content_type} for {platform}.
                TOPIC: {topic}
                AUDIENCE: {target_audience}
                TONE: {tone}
                LENGTH: {length}
                
                REQUIREMENTS:
                - Use platform-specific formatting.
                - { "Include a creative analogy to explain complex concepts." if include_analogy else "" }
                - { "Provide 2 distinct variants (Version A and Version B) for A/B testing." if ab_testing else "" }
                """
                result = call_gemini(prompt, "creation")
                if result:
                    st.session_state['generated_result'] = result
                    st.session_state['generated_title'] = f"{content_type}: {topic[:30]}..."
        st.markdown('</div>', unsafe_allow_html=True)

    # Result Display area
    if 'generated_result' in st.session_state:
        st.markdown("### 📄 Generated Result")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(st.session_state['generated_result'])
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Save to CMS Quick Action
        if st.button("💾 Save to CMS"):
            CMS.save_content(st.session_state['generated_title'], st.session_state['generated_result'], [content_type, platform])
            st.success("Saved to Content Library!")

# --- 2. Transformation Engine ---
elif "Transformation" in app_mode:
    st.header("🔄 Content Transformation Engine")
    
    input_text = st.text_area("Paste Content to Transform", height=200)
    
    col1, col2 = st.columns(2)
    with col1:
        trans_type = st.selectbox("Transformation Type", 
            ["Summarize to Tweet Thread", "Convert to Blog Post", "Create Quiz/Flashcards", "Simplify for Kids", "Executive Summary"])
    with col2:
        context_opt = st.text_input("Additional Context (Optional)", placeholder="E.g., Focus on financial implications...")

    if st.button("⚡ Transform"):
        if input_text:
            with st.spinner("Transforming..."):
                prompt = f"""
                TASK: Perform the following transformation on the input text.
                TYPE: {trans_type}
                CONTEXT: {context_opt}
                
                INPUT TEXT:
                {input_text}
                """
                result = call_gemini(prompt, "transformation")
                if result:
                    st.markdown("### 🔄 Result")
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown(result)
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("Please provide input text.")

# --- 3. Smart CMS ---
elif "CMS" in app_mode:
    st.header("📂 Smart Content Management System")
    
    # List View
    content_items = CMS.list_content()
    
    # Filter
    search_q = st.text_input("🔍 Search Content Library", placeholder="Search by title or tags...")
    
    col1, col2 = st.columns([1, 2])
    
    selected_file = None
    
    with col1:
        st.subheader("Library")
        for item in content_items:
            if search_q.lower() in item['title'].lower() or search_q.lower() in str(item['tags']).lower():
                # Item Card
                with st.container():
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"📅 {item['timestamp'][:10]} | v{item['version']} | {item['status']}")
                    if st.button("Open", key=f"open_{item['id']}_{item['version']}"):
                        st.session_state['cms_active_file'] = item
                    st.markdown("---")

    with col2:
        if 'cms_active_file' in st.session_state:
            active = st.session_state['cms_active_file']
            st.subheader(f"📝 Editor: {active['title']}")
            
            # Metadata bar
            c1, c2, c3 = st.columns(3)
            c1.info(f"Version: {active['version']}")
            c2.info(f"Status: {active['status']}")
            
            # Editor
            new_content = st.text_area("Content", value=active['content'], height=400)
            
            # Actions
            ac1, ac2 = st.columns(2)
            if ac1.button("💾 Save New Version"):
                CMS.save_content(
                    active['title'], 
                    new_content, 
                    active['tags'], 
                    status="published", 
                    version=active['version']+1, 
                    parent_id=active['id']
                )
                st.success("New version saved!")
                time.sleep(1)
                st.rerun()
                
            if ac2.button("🤖 AI Analyze / Refine"):
                with st.spinner("AI is analyzing..."):
                    prompt = f"Analyze this content and suggest improvements for clarity and engagement:\n\n{new_content}"
                    analysis = call_gemini(prompt, "cms")
                    st.info(analysis)
        else:
            st.info("Select an item from the library to edit.")

# --- 4. Personalization Engine ---
elif "Personalization" in app_mode:
    st.header("👤 Personalization & Analytics Engine")
    
    st.markdown("""
    This engine simulates user behavior to help you tailor content.
    """)
    
    persona = st.selectbox("Select User Persona to Simulate", 
        ["Busy CEO (Skims, needs value fast)", "Junior Developer (Needs details & examples)", "Skeptical Investor (Needs data & proof)"])
    
    input_content = st.text_area("Content to Test against Persona", height=200)
    
    if st.button("🔮 Run Simulation"):
        if input_content:
            with st.spinner(f"Simulating interaction for {persona}..."):
                prompt = f"""
                Roleplay as this persona: {persona}.
                Read the following content.
                
                PROVIDE:
                1. Your immediate reaction (Emotion/Interest).
                2. Did you finish reading? Where did you drop off?
                3. What was confusing or irrelevant to you?
                4. A rewritten version of the Intro that would have hooked you better.
                
                CONTENT:
                {input_content}
                """
                feedback = call_gemini(prompt, "personalization")
                st.markdown("### 📊 Simulation Results")
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown(feedback)
                st.markdown('</div>', unsafe_allow_html=True)
