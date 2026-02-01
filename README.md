# ⚡ Content OS v4.0

A high-performance, AI-driven content generation and management system. This platform allows users to create, transform, and manage professional-grade content using the Google Gemini model, featuring a unified backend accessible via both a **Streamlit Dashboard** and a **FastAPI Backend**.

## 🌟 Key Features

### 🎨 AI Content Creation Engine
- **Multiple Modes**: Blog posts, Social Media, Video Scripts, Newsletters, Study Notes, Marketing Copy, Technical Documentation.
- **Granular Controls**: Target audience selector, Tone control, Length management, Platform-specific formatting, and Explanation depth.
- **Advanced Options**: A/B variant generation, Human-like rewriting, and Analogy-based explanations.

### 🔄 Content Transformation Engine
- **One-to-Many**: Convert long articles to social threads, videos to blogs, and notes to quizzes.
- **Semantic Refinement**: Simplification (ELI5), Expansion, Reframing, and Counter-argument generation.

### 📂 Smart Content Management System (CMS)
- **Git-Like Versioning**: Track every change, compare versions with diff-checking, and rollback to previous states.
- **Folder Organization**: Categorize projects into custom folders.
- **Metadata Tracking**: Automated word count, reading time, and engagement simulation.

### 🧠 Personalization Engine
- **Behavior Tracking**: Session duration, interaction counts, and project engagement metrics.
- **Adaptive AI**: Suggests summaries and tone adjustments based on user preferences and past performance.

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Google Gemini API Key

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Ashwath-Raj/AI-enhanced-Content-Creation.git
   cd AI-enhanced-Content-Creation
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   Create a `.env` file in the root directory and add your API key:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

### 🖥️ Running the Application

#### Option A: Interactive Dashboard (Streamlit)
Best for end-users and content managers.
```bash
streamlit run app.py
```

#### Option B: Professional API Backend (FastAPI)
Best for developers integrating Content OS into other apps.
```bash
python main_api.py
```
- **API Entry**: `http://127.0.0.1:8000`
- **Interactive Documentation**: `http://127.0.0.1:8000/docs`

## 📂 Project Structure
- `app.py`: The Streamlit dashboard.
- `main_api.py`: FastAPI server implementation.
- `core.py`: Shared core logic and AI integration.
- `smart_cms_data/`: Local storage for projects and version history.

## 🔐 Security
- API keys are managed via environment variables and are excluded from version control via `.gitignore`.
- Input sanitization is applied to prevent XSS in rendered views.

---

Built with AI by [Ashwath-Raj](https://github.com/Ashwath-Raj)
