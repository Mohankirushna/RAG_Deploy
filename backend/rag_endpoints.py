from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import asyncio
from pathlib import Path
import shutil
import uuid

# Import the RAG service
import sys
sys.path.append(str(Path(__file__).parent.parent))
from app.rag_service import RAGService
from app.config import settings

# Create router
router = APIRouter()

# Initialize RAG service
rag_service = RAGService(index_name="web_rag")

# Models
class QueryRequest(BaseModel):
    query: str
    top_k: int = 3

class QueryResponse(BaseModel):
    answer: str
    contexts: List[Dict[str, Any]]
    status: str = "success"

class UploadResponse(BaseModel):
    status: str
    message: str
    document_id: str
    chunk_count: int = 0

# Routes
@router.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF document"""
    try:
        # Create uploads directory if it doesn't exist
        os.makedirs("../uploads", exist_ok=True)
        
        # Save the uploaded file
        file_extension = ".pdf"
        document_id = str(uuid.uuid4())
        file_path = f"../uploads/{document_id}{file_extension}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the document
        result = await rag_service.process_and_store_document(
            file_path=file_path,
            file_extension=file_extension
        )
        
        return {
            "status": "success",
            "message": f"File {file.filename} processed successfully",
            "document_id": document_id,
            "chunk_count": result.get("chunk_count", 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query-pdf", response_model=QueryResponse)
async def query_pdf(request: QueryRequest):
    """Query the RAG system"""
    try:
        print(f"Received query: {request.query}")
        
        # Validate input
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
            
        # Process the query
        response = await rag_service.query(
            query_text=request.query,
            top_k=request.top_k
        )
        
        print(f"Query response: {response}")
        
        if not response.get("success", False):
            error_detail = response.get("details", response.get("error", "Unknown error"))
            print(f"Query failed: {error_detail}")
            
            # Return a more detailed error response
            return JSONResponse(
                status_code=200,  # Return 200 to allow frontend to handle the error
                content={
                    "success": False,
                    "error": "Failed to process query",
                    "details": str(error_detail),
                    "answer": "I'm sorry, I encountered an error while processing your request. Please try again.",
                    "contexts": []
                }
            )
            
        # Return successful response
        return {
            "success": True,
            "answer": response.get("answer", "No answer generated"),
            "contexts": response.get("contexts", [])
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        import traceback
        error_detail = f"Unexpected error: {str(e)}\n\n{traceback.format_exc()}"
        print(f"Error in query_pdf: {error_detail}")
        
        # Return a user-friendly error message
        return JSONResponse(
            status_code=200,  # Return 200 to allow frontend to handle the error
            content={
                "success": False,
                "error": "An unexpected error occurred",
                "details": "Please try again later or contact support if the issue persists.",
                "answer": "I'm sorry, I encountered an unexpected error. Please try again.",
                "contexts": []
            }
        )

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}
