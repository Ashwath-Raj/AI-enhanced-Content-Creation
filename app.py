
import streamlit as st
import os
from dotenv import load_dotenv


# Load environment variables
load_dotenv(override=True)

try:
    import requests
    from bs4 import BeautifulSoup
    import google.generativeai as genai
    dependencies_installed = True
except ImportError as e:
    dependencies_installed = False
    missing_module = str(e)

# Valid Model Name
MODEL_NAME = 'gemini-2.5-flash'

# Page Configuration
st.set_page_config(
    page_title="Content Operating System",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Aesthetics
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    h1 {
        color: #1e1e1e;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .stTextArea textarea {
        background-color: #ffffff;
        color: #333333;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    .stButton>button {
        background: linear-gradient(45deg, #6b4cff, #9072ff);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(107, 76, 255, 0.2);
    }
    .content-box {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border-left: 4px solid #6b4cff;
    }
    .metric-card {
        background: linear-gradient(135deg, #ffffff, #f0f2f6);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e1e4e8;
    }
</style>
""", unsafe_allow_html=True)

if not dependencies_installed:
    st.error(f"❌ Missing Dependency: {missing_module}")
    st.warning("""
    **Please install the required libraries to run this app.**
    
    Run the following command in your terminal:
    ```bash
    pip install google-generativeai beautifulsoup4 requests python-dotenv
    ```
    """)
    st.stop()


# Sidebar for Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Check for API Key
    api_key_check = os.getenv("GEMINI_API_KEY")
    if not api_key_check:
        st.error("⚠️ GEMINI_API_KEY not found in .env file")
        st.info("Please create a .env file with your GEMINI_API_KEY.")
    else:
        st.success(f"API Key Loaded ({len(api_key_check)} chars) ✅")
    
    st.markdown("---")
    st.markdown("### 🎯 Content Settings")
    tone_student = st.slider("Simplification Level (Student)", 1, 10, 8)
    tone_exec = st.slider("Formality Level (Executive)", 1, 10, 9)

# Main Content Area
st.title("⚡ Content Operating System")
st.markdown("Transform your input into multi-format content customized for different audiences.")

# Input Section
input_method = st.radio("Choose Input Method", ["Text Paste", "URL"])
input_content = ""

if input_method == "Text Paste":
    input_content = st.text_area("Paste your source content here", height=200)
else:
    url_input = st.text_input("Enter Article URL")
    if url_input:
        try:
            response = requests.get(url_input)
            soup = BeautifulSoup(response.content, 'html.parser')
            # Basic textual extraction; can be improved
            paragraphs = soup.find_all('p')
            input_content = "\n\n".join([p.get_text() for p in paragraphs])
            with st.expander("Preview Extracted Text"):
                st.write(input_content[:500] + "...")
        except Exception as e:
            st.error(f"Error fetching URL: {e}")

# Logic Functions
def generate_content(content):
    # Fetch and clean API key
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    
    genai.configure(api_key=api_key)
    # Using gemini-pro which is generally available
    model = genai.GenerativeModel(MODEL_NAME) 

    prompt = f"""
    You are the AI agent inside a Content Operating System. 
    Your role is to process the following input, transform it into multiple content formats, 
    personalize it for different audiences, and generate insights.

    INPUT:
    {content}

    TASKS:
    1. Summarize the input into a concise blog post.
    2. Transform the blog post into a social media thread (5–7 posts).
    3. Personalize the content for two audiences:
       - Audience A: Students (simpler tone, engaging examples)
       - Audience B: Executives (formal tone, strategic framing)
    4. Provide an analytics-style explanation:
       - Which version is more likely to perform better online?
       - Why? (clarity, tone, relevance, engagement factors)

    OUTPUT FORMAT (Return valid JSON):
    {{
      "blog_post": "...",
      "social_thread": ["post1", "post2", "..."],
      "student_version": "...",
      "executive_version": "...",
      "insight": "..."
    }}
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return response.text
    except Exception as e:
        st.error(f"API Error (Model: {MODEL_NAME}): {e}")
        return None

import json

if st.button("🚀 Generate Content Assets"):
    if not os.getenv("GEMINI_API_KEY"):
        st.warning("Please add your GEMINI_API_KEY to the .env file.")
    elif not input_content:
        st.warning("Please provide input content.")
    else:
        with st.spinner("Processing content..."):
            result_json_str = generate_content(input_content)
            
            if result_json_str:
                try:
                    data = json.loads(result_json_str)
                    
                    # Layout using tabs
                    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Blog Post", "🧵 Social Thread", "🎓 Student View", "💼 Executive View", "📊 Insights"])
                    
                    with tab1:
                        st.markdown('<div class="content-box">', unsafe_allow_html=True)
                        st.subheader("Blog Post")
                        st.write(data.get("blog_post", "No content generated."))
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                    with tab2:
                        st.markdown('<div class="content-box">', unsafe_allow_html=True)
                        st.subheader("Social Media Thread")
                        for i, post in enumerate(data.get("social_thread", []), 1):
                            st.info(f"**Post {i}:** {post}")
                        st.markdown('</div>', unsafe_allow_html=True)

                    with tab3:
                        st.markdown('<div class="content-box">', unsafe_allow_html=True)
                        st.subheader("Student Version")
                        st.write(data.get("student_version", "No content."))
                        st.markdown('</div>', unsafe_allow_html=True)

                    with tab4:
                        st.markdown('<div class="content-box">', unsafe_allow_html=True)
                        st.subheader("Executive Version")
                        st.write(data.get("executive_version", "No content."))
                        st.markdown('</div>', unsafe_allow_html=True)

                    with tab5:
                        st.markdown('<div class="content-box">', unsafe_allow_html=True)
                        st.subheader("Performance Insights")
                        st.write(data.get("insight", "No insights."))
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                except json.JSONDecodeError:
                    st.error("Failed to parse AI response. Raw output:")
                    st.text(result_json_str)
