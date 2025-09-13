from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import shutil
import uuid
from pathlib import Path
import uvicorn
import sys

# Add the parent directory to the path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

# Import RAG endpoints
from backend.rag_endpoints import router as rag_router

# Configuration
UPLOAD_FOLDER = "../uploads"
INDEX_FOLDER = "../indices"
MODEL_NAME = "mistral"  # Ollama model name

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(INDEX_FOLDER, exist_ok=True)

app = FastAPI(title="RAG API with Local Mistral Model")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include RAG routes
app.include_router(rag_router, prefix="", tags=["RAG Operations"])

# Models (kept for backward compatibility)
from pydantic import BaseModel
from typing import List, Dict, Any

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool

# Routes
@app.get("/")
async def root():
    return {"message": "RAG API with Local Mistral Model"}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check if the API and model are ready"""
    try:
        # Simple check if Ollama is running
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_loaded = any(m.get("name", "").startswith(MODEL_NAME) for m in models)
            return {
                "status": "ok",
                "model_loaded": model_loaded,
                "models": [m.get("name") for m in models]
            }
        return {"status": "error", "model_loaded": False, "error": "Failed to connect to Ollama"}
    except Exception as e:
        return {"status": f"error: {str(e)}", "model_loaded": False}

@app.get("/model-status")
async def model_status():
    """Check if the model is loaded and ready"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_loaded = any(m.get("name", "").startswith(MODEL_NAME) for m in models)
            return {
                "status": "ready" if model_loaded else "model_not_loaded",
                "model_loaded": model_loaded,
                "models": [m.get("name") for m in models]
            }
        return {"status": "error", "error": "Failed to connect to Ollama"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
