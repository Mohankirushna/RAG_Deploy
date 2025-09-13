from typing import List, Dict, Any, Optional, Union, BinaryIO
import os
import hashlib
import json
from datetime import datetime
from pathlib import Path

from app.document_processor import DocumentProcessor
from app.embedding import LocalEmbedder
from app.vector_store import DocumentStore
from app.config import settings

class RAGService:
    """
    Main RAG service that orchestrates document processing, embedding, and retrieval.
    """
    
    def __init__(self, index_name: str = "default"):
        """
        Initialize the RAG service.
        
        Args:
            index_name: Name of the index to use/create
        """
        self.index_name = index_name
        self.document_processor = DocumentProcessor()
        self.embedder = LocalEmbedder()
        self.document_store = DocumentStore(
            index_dir=settings.INDEX_FOLDER,
            index_name=index_name
        )
    
    async def process_and_store_document(
        self, 
        file_path: Union[str, BinaryIO], 
        file_extension: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a document and store it in the document store.
        
        Args:
            file_path: Path to the document or file-like object
            file_extension: Optional file extension (e.g., '.pdf', '.docx', '.txt')
            metadata: Additional metadata to store with the document
            
        Returns:
            Dictionary with processing results
        """
        if metadata is None:
            metadata = {}
            
        # Process the document
        try:
            # Process the document and get the full text
            if isinstance(file_path, BinaryIO):
                text = self.document_processor.process_document_from_stream(file_path, file_extension)
            else:
                text = self.document_processor.process_document(file_path, file_extension)
            
            # Chunk the text into smaller pieces for processing
            chunks = self.document_processor.chunk_text(
                text,
                chunk_size=settings.CHUNK_SIZE,
                overlap=settings.CHUNK_OVERLAP
            )
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing document: {str(e)}",
                "document_id": None
            }
        
        if not chunks or not any(chunks):
            return {
                "success": False,
                "error": "No text content could be extracted from the document",
                "document_id": None
            }
            
        # Generate a document ID
        doc_id = self._generate_document_id(file_path, "".join(chunks))
        metadata.update({
            "document_id": doc_id,
            "source": file_path.name if hasattr(file_path, 'name') else str(file_path),
            "chunk_count": len(chunks)
        })
        
        # Add chunks to document store with metadata
        try:
            # Create metadata for each chunk
            metadatas = []
            for i, chunk in enumerate(chunks):
                chunk_meta = metadata.copy()
                chunk_meta.update({
                    "chunk_id": f"{doc_id}_chunk_{i}",
                    "chunk_index": i,
                    "chunk_count": len(chunks)
                })
                metadatas.append(chunk_meta)
            
            # Add documents to the store
            await self.document_store.add_documents(chunks, metadatas)
            
            # Save the index
            await self.document_store.save()
            
            return {
                "success": True,
                "document_id": doc_id,
                "chunk_count": len(chunks),
                "message": f"Successfully processed and stored document with {len(chunks)} chunks"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error storing document: {str(e)}",
                "document_id": doc_id
            }
    
    async def query(
        self, 
        query_text: str, 
        top_k: Optional[int] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the RAG system with a question.
        
        Args:
            query_text: The question to ask
            top_k: Number of results to return (defaults to settings.TOP_K_RESULTS)
            filter_conditions: Optional filters to apply to the search
            
        Returns:
            Dictionary with the generated answer and relevant context
        """
        if top_k is None:
            top_k = settings.TOP_K_RESULTS
            
        try:
            if not query_text or not query_text.strip():
                raise ValueError("Query text cannot be empty")
                
            print(f"Processing query: {query_text}")
            # Generate query embedding
            try:
                query_embedding = await self.embedder.generate_embeddings([query_text])
                query_embedding = self.embedder.normalize_embeddings(query_embedding)[0]
                print(f"Generated query embedding of length: {len(query_embedding)}")
            except Exception as e:
                print(f"Error generating embeddings: {str(e)}")
                raise
            
            # Perform similarity search
            try:
                print(f"Performing similarity search with top_k={top_k}")
                results = await self.document_store.similarity_search(query_text, k=top_k)
                print(f"Found {len(results)} results")
            except Exception as e:
                print(f"Error in similarity search: {str(e)}")
                raise
            
            # Prepare results
            contexts = []
            for result in results:
                context = {
                    "text": result.get("text", ""),
                    "source": result.get("source", "unknown"),
                    "document_id": result.get("document_id", ""),
                    "chunk_id": result.get("chunk_id", ""),
                    "score": result.get("score", 0.0)
                }
                contexts.append(context)
            
            # Generate response using the LLM
            try:
                print("Generating response with LLM...")
                answer = await self._generate_response(query_text, contexts)
                print("Successfully generated response")
                
                return {
                    "success": True,
                    "answer": answer,
                    "contexts": contexts,
                    "query_embedding": query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding
                }
            except Exception as e:
                print(f"Error generating LLM response: {str(e)}")
                raise
            
        except Exception as e:
            import traceback
            error_detail = f"Error processing query: {str(e)}\n\n{traceback.format_exc()}"
            print(f"Error in RAGService.query: {error_detail}")
            return {
                "success": False,
                "error": f"Error processing query: {str(e)}",
                "details": error_detail
            }
    
    async def _generate_response(
        self, 
        query: str, 
        contexts: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a response using a local Mistral model via Ollama based on the query and retrieved contexts.
        
        Args:
            query: The user's question
            contexts: List of relevant context dictionaries
            
        Returns:
            Generated response text
        """
        try:
            import requests
            import json
            
            if not contexts:
                print("Warning: No contexts provided for response generation")
                return "I couldn't find enough relevant information to answer your question."
            
            # Prepare the context text
            context_text = "\n\n---\n".join([
                f"Context {i+1} (from {ctx.get('source', 'unknown')}):\n{ctx.get('text', '')}"
                for i, ctx in enumerate(contexts)
            ])
            
            # Create the prompt for the LLM
            prompt = f"""You are a helpful AI assistant. Answer the question based on the provided context.
            If the context doesn't contain relevant information, say that you don't know the answer.
            Be concise and to the point.

            Context:
            {context_text}
            
            Question: {query}
            
            Answer:"""
            
            # Ollama API endpoint (assuming default configuration)
            url = "http://localhost:11434/api/generate"
            
            # Prepare the request payload for Mistral model
            payload = {
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_ctx": 4096  # Context window size
                }
            }
            
            print(f"Sending request to Ollama API at {url}")
            print(f"Prompt length: {len(prompt)} characters")
            
            # Make the request to Ollama
            try:
                print("Sending request to Ollama...")
                response = requests.post(url, json=payload, timeout=60)  # 60 second timeout
                print(f"Received response with status code: {response.status_code}")
                
                # Check for HTTP errors
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
                
                if 'response' not in result:
                    print(f"Unexpected response format from Ollama: {result}")
                    return "I'm sorry, I encountered an issue generating a response. Please try again."
                    
                return result.get('response', 'No response generated')
                
            except requests.exceptions.RequestException as e:
                print(f"Error making request to Ollama: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Response status: {e.response.status_code}")
                    print(f"Response body: {e.response.text}")
                raise Exception(f"Failed to communicate with the language model: {str(e)}")
                
            except Exception as e:
                import traceback
                error_detail = f"Error in _generate_response: {str(e)}\n\n{traceback.format_exc()}"
                print(error_detail)
                return f"I'm sorry, I encountered an error while generating a response. Please try again later. Here are the relevant contexts I found:\n\n{context_text}"
        
        except Exception as e:
            import traceback
            error_detail = f"Error in _generate_response (outer): {str(e)}\n\n{traceback.format_exc()}"
            print(error_detail)
            return "I'm sorry, I encountered an error while processing your request. Please try again later."
    
    def _generate_document_id(self, file_path: str, text: str) -> str:
        """
        Generate a unique document ID based on file path and content.
        
        Args:
            file_path: Path to the document
            text: Document content
            
        Returns:
            Unique document ID
        """
        # Use both file path and content to generate a unique ID
        unique_str = f"{file_path}:{len(text)}:{hashlib.md5(text.encode('utf-8')).hexdigest()}"
        return hashlib.sha256(unique_str.encode('utf-8')).hexdigest()
    
    async def get_document_count(self) -> int:
        """Get the total number of document chunks in the store."""
        return await self.document_store.get_document_count()
    
    async def clear_index(self) -> None:
        """Clear all documents from the index."""
        await self.document_store.clear()
        await self.document_store.save()
