from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
from core import call_gemini, ContentManager, IngestionClient, CMS_ROOT, check_env_security

app = FastAPI(title="Content OS API", version="4.0")

# Security Check on Startup
sec_ok, sec_msg = check_env_security()
if not sec_ok:
    print(sec_msg)
    # Don't exit here to allow dev to see docs, but endpoints will fail if keys are missing
cms = ContentManager()
ingest_client = IngestionClient()

# --- Models ---

class CreationRequest(BaseModel):
    mode: str
    input_context: str
    audience: Optional[str] = "General Tech"
    tone: Optional[str] = "Professional"
    length: Optional[str] = "Medium"
    depth: Optional[str] = "Intermediate"
    platform: Optional[str] = "Generic"
    adv_ab: Optional[bool] = False
    adv_human: Optional[bool] = False
    adv_analogy: Optional[bool] = False
    save_folder: Optional[str] = "General"

class TransformationRequest(BaseModel):
    content: str
    trans_mode: str
    sem_mode: str

class CommitRequest(BaseModel):
    folder: str
    project_id: str
    content: str
    title: str
    tags: List[str]
    status: str
    message: Optional[str] = "Update"
    extra_meta: Optional[Dict[str, Any]] = None

class CreateProjectRequest(BaseModel):
    title: str
    folder: str
    content: str
    tags: Optional[List[str]] = None
    extra_meta: Optional[Dict[str, Any]] = None

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to Content OS API", "status": "online"}

# 1. AI Content Creation Engine
@app.post("/create")
async def create_content(req: CreationRequest):
    prompt = f"""
    ACT AS: Expert Content Creator.
    TASK: Write a {req.mode}.
    SOURCE MATERIAL: {req.input_context[:20000]}
    
    TARGET AUDIENCE: {req.audience}
    TONE: {req.tone}
    LENGTH: {req.length}
    DEPTH: {req.depth}
    PLATFORM: {req.platform}
    
    ADVANCED INSTRUCTIONS:
    - { "Create 2 distinct variants (Option A and Option B)" if req.adv_ab else "Single high-quality version" }
    - { "Use natural, human-like phrasing (avoid AI cliches)" if req.adv_human else "" }
    - { "Explain complex concepts using simple analogies" if req.adv_analogy else "" }
    """
    
    result = call_gemini(prompt, "creation")
    if not result or result.startswith("Error"):
        raise HTTPException(status_code=500, detail=result)
    
    # Optional auto-save
    tags = ["AI-Gen", req.mode, req.platform]
    if req.adv_ab: tags.append("A/B Testing")
    
    gen_meta = {
        "mode": req.mode,
        "tone": req.tone,
        "platform": req.platform,
        "audience": req.audience
    }
    
    project_id = cms.create_project(
        title=f"{req.mode}: {req.audience[:15]}...",
        folder=req.save_folder,
        content=result,
        tags=tags,
        extra_meta=gen_meta
    )
    
    return {"content": result, "project_id": project_id, "folder": req.save_folder}

# 2. Content Transformation Engine
@app.post("/transform")
async def transform_content(req: TransformationRequest):
    prompt = f"""
    TASK: Content Transformation
    SOURCE: {req.content[:15000]}
    
    PRIMARY GOAL: Convert to {req.trans_mode}
    SECONDARY REFINEMENT: {req.sem_mode}
    
    Keep the core meaning but adapt strictly to the new format.
    """
    result = call_gemini(prompt, "transformation")
    if not result or result.startswith("Error"):
        raise HTTPException(status_code=500, detail=result)
    
    return {"content": result}

# 3. Smart Content Management System (CMS)
@app.get("/cms/folders")
def list_folders():
    return {"folders": cms.get_folders()}

@app.post("/cms/folders/{folder}")
def create_folder(folder: str):
    os.makedirs(os.path.join(CMS_ROOT, folder), exist_ok=True)
    return {"message": f"Folder {folder} created."}

@app.get("/cms/projects")
def list_projects():
    return {"projects": cms.list_all_content()}

@app.get("/cms/project/{folder}/{project_id}")
def get_project(folder: str, project_id: str):
    meta = cms.get_meta(folder, project_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Project not found")
    history = cms.get_history(folder, project_id)
    return {"metadata": meta, "history": history}

@app.post("/cms/project")
def create_new_project(req: CreateProjectRequest):
    pid = cms.create_project(req.title, req.folder, req.content, req.tags, req.extra_meta)
    return {"project_id": pid}

@app.post("/cms/project/commit")
def commit_version(req: CommitRequest):
    cms.commit_version(req.folder, req.project_id, req.content, req.title, req.tags, req.status, req.message, req.extra_meta)
    return {"message": "Version committed successfully."}

# 4. Personalization Engine
@app.post("/personalize/log_interaction")
def log_interaction(interaction_type: str, details: Optional[Dict[str, Any]] = None):
    # In a real app, this would save to a DB. For now, we just acknowledge.
    return {"message": f"Interaction {interaction_type} logged.", "details": details}

@app.get("/personalize/metrics")
def get_user_metrics():
    # Return mock metrics as seen in the UI
    return {
        "session_duration_min": 5.2,
        "interactions": 12,
        "projects_viewed": 3,
        "tone_preferences": ["Professional", "Casual"]
    }

@app.post("/personalize/summarize")
def personalize_summary(req: Dict[str, Any]):
    content = req.get("content", "")
    user_prefs = req.get("user_prefs", {})
    prompt = f"""
    Summarize this content.
    USER PREFERENCES: {user_prefs}
    
    Content: {content[:5000]}
    """
    result = call_gemini(prompt, "personalization")
    return {"summary": result}

@app.post("/personalize/adapt_tone")
def adapt_tone(content: str, target_tone: str):
    prompt = f"Rewrite this content to match a {target_tone} tone. Content: {content[:2000]}"
    result = call_gemini(prompt, "personalization")
    return {"adapted_content": result}

# 5. Ingestion Helpers
@app.post("/ingest/url")
async def ingest_url(url: str):
    res = ingest_client.ingest_url(url)
    return res

@app.post("/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    content = await file.read()
    res = ingest_client.ingest_file(file.filename, content, file.content_type)
    return res

@app.get("/cms/project/{folder}/{project_id}/compare")
def compare_versions(folder: str, project_id: str, v1: str, v2: str):
    import difflib
    history = cms.get_history(folder, project_id)
    content1 = next((v['content'] for v in history if v['version_id'] == v1), None)
    content2 = next((v['content'] for v in history if v['version_id'] == v2), None)
    
    if content1 is None or content2 is None:
        raise HTTPException(status_code=404, detail="Version not found")
    
    diff = list(difflib.unified_diff(content1.splitlines(), content2.splitlines()))
    return {"diff": diff}

if __name__ == "__main__":
    print("🚀 Content OS API is starting...")
    print("📝 Access Swagger UI at: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)
