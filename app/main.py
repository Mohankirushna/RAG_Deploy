import os
import uvicorn
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import time

from .rag_service import RAGService
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RAG API",
    description="Retrieval-Augmented Generation API powered by Google Gemini",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG service
rag_service = RAGService()

# Create uploads directory if it doesn't exist
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "rag-api",
        "version": "1.0.0",
        "document_count": rag_service.get_document_count()
    }

# Upload document endpoint
@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = None
):
    """
    Upload and index a document.
    
    Args:
        file: The document file to upload (PDF, DOCX, or TXT)
        metadata: Optional JSON string containing metadata for the document
    """
    # Validate file type
    allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Supported types: {', '.join(allowed_types)}"
        )
    
    # Parse metadata if provided
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
            if not isinstance(metadata_dict, dict):
                raise ValueError("Metadata must be a JSON object")
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid metadata format. Must be a valid JSON object."
            )
    
    # Save the uploaded file temporarily
    try:
        file_extension = Path(file.filename).suffix if file.filename else None
        temp_file_path = os.path.join(settings.UPLOAD_FOLDER, file.filename or f"temp_upload_{int(time.time())}")
        
        # Ensure upload directory exists
        os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
        
        # Save the uploaded file
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            if not content:
                raise ValueError("Uploaded file is empty")
            buffer.write(content)
        
        # Process and index the document
        try:
            result = await rag_service.process_and_store_document(
                file_path=temp_file_path,
                file_extension=file_extension,
                metadata={
                    "original_filename": file.filename,
                    "content_type": file.content_type,
                    **metadata_dict
                }
            )
            
            if not result.get("success"):
                error_msg = result.get("error", "Failed to process document")
                logger.error(f"Document processing failed: {error_msg}")
                raise HTTPException(
                    status_code=400,
                    detail=error_msg
                )
            
            return {
                "success": True,
                "document_id": result.get("document_id"),
                "num_chunks": result.get("num_chunks"),
                "total_documents": rag_service.get_document_count(),
                "message": "Document processed and indexed successfully"
            }
            
        except HTTPException:
            raise  # Re-raise HTTP exceptions as-is
            
        except Exception as e:
            logger.exception("Error processing document")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process document: {str(e)}"
            )
            
    except Exception as e:
        logger.exception("Error handling file upload")
        raise HTTPException(
            status_code=400,
            detail=f"Error handling file upload: {str(e)}"
        )
        
    finally:
        # Clean up the temporary file if it exists
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except Exception as e:
            logger.warning(f"Failed to remove temporary file {temp_file_path}: {str(e)}")

# Query endpoint
@app.post("/query")
async def query(
    query: str,
    top_k: Optional[int] = None,
    filter_conditions: Optional[Dict[str, Any]] = None
):
    """
    Query the RAG system with a question.
    
    Args:
        query: The question to ask
        top_k: Number of results to return (defaults to app settings)
        filter_conditions: Optional filters to apply to the search
    """
    if not query or not query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty"
        )
    
    try:
        result = await rag_service.query(
            query_text=query,
            top_k=top_k,
            filter_conditions=filter_conditions
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error processing query")
            )
        
        return {
            "success": True,
            "answer": result.get("answer", ""),
            "contexts": result.get("contexts", []),
            "query_embedding": result.get("query_embedding")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

# Get document count endpoint
@app.get("/documents/count")
async def get_document_count():
    """Get the total number of document chunks in the index."""
    return {
        "success": True,
        "count": rag_service.get_document_count()
    }

# Clear index endpoint (for testing/development)
@app.delete("/documents")
async def clear_index():
    """Clear all documents from the index."""
    rag_service.clear_index()
    return {
        "success": True,
        "message": "Index cleared successfully",
        "count": rag_service.get_document_count()
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "RAG API",
        "version": "1.0.0",
        "description": "Retrieval-Augmented Generation API powered by Google Gemini",
        "endpoints": [
            {"path": "/health", "method": "GET", "description": "Health check"},
            {"path": "/upload", "method": "POST", "description": "Upload and index a document"},
            {"path": "/query", "method": "POST", "description": "Query the RAG system"},
            {"path": "/documents/count", "method": "GET", "description": "Get document count"},
            {"path": "/documents", "method": "DELETE", "description": "Clear all documents (for testing)"}
        ]
    }

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
