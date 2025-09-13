import os
import logging
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class LocalEmbedder:
    """
    Handles text embedding generation using a local model.
    """
    
    def __init__(self, model_name: str = None):
        """Initialize the local embedder with a model name."""
        self.model_name = model_name or settings.EMBEDDING_MODEL
        logger.info(f"Loading local embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text chunks using a local model.
        
        Args:
            texts: List of text strings to generate embeddings for
            
        Returns:
            List of embedding vectors (list of floats)
        """
        if not texts:
            return []
            
        try:
            # Generate embeddings using the local model
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Convert numpy arrays to lists for JSON serialization
            return [embedding.tolist() for embedding in embeddings]
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise ValueError(f"Error generating embeddings: {str(e)}")
    
    @staticmethod
    def normalize_embeddings(embeddings: List[List[float]]) -> np.ndarray:
        """
        Normalize embeddings to unit length.
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            np.ndarray: Normalized embeddings
        """
        if not embeddings:
            return np.array([])
            
        # Convert to numpy array if not already
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)
            
        # Normalize each embedding to unit length
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        return embeddings / norms
