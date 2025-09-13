import os
import json
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pickle

from app.embedding import LocalEmbedder

class FAISSVectorStore:
    """
    A class to handle vector storage and similarity search using FAISS.
    """
    
    def __init__(self, index_path: Optional[str] = None, dimension: int = 768):
        """
        Initialize the FAISS vector store.
        
        Args:
            index_path: Path to load/save the FAISS index
            dimension: Dimension of the embedding vectors
        """
        self.dimension = dimension
        self.index_path = index_path
        self.metadata_path = None
        self.index = None
        self.metadata = []
        
        # Initialize FAISS index
        if index_path and os.path.exists(index_path):
            self.load_index(index_path)
        else:
            # Create a new index
            self.index = faiss.IndexFlatL2(dimension)
    
    def add_vectors(self, vectors: np.ndarray, metadatas: List[Dict[str, Any]]) -> None:
        """
        Add vectors and their metadata to the index.
        
        Args:
            vectors: Numpy array of shape (n, dimension)
            metadatas: List of metadata dictionaries for each vector
        """
        if self.index is None:
            self.index = faiss.IndexFlatL2(vectors.shape[1])
        
        # Convert to float32 if needed
        if vectors.dtype != np.float32:
            vectors = vectors.astype(np.float32)
        
        # Add vectors to the index
        self.index.add(vectors)
        
        # Add metadata
        self.metadata.extend(metadatas)
    
    def similarity_search(
        self, 
        query_vector: np.ndarray, 
        k: int = 5
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        """
        Perform a similarity search.
        
        Args:
            query_vector: Query vector of shape (dimension,)
            k: Number of results to return
            
        Returns:
            Tuple of (list of metadata dicts, list of distances)
        """
        if self.index is None or len(self.metadata) == 0:
            return [], []
        
        # Ensure query_vector is 2D and float32
        query_vector = np.array(query_vector, dtype=np.float32)
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        # Search the index
        distances, indices = self.index.search(query_vector, min(k, len(self.metadata)))
        
        # Get the results
        results = []
        result_distances = []
        
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
                
            result = self.metadata[idx].copy()
            distance = float(distances[0][i])
            result['distance'] = distance
            results.append(result)
            result_distances.append(distance)
        
        return results, result_distances
    
    def save_index(self, path: Optional[str] = None) -> None:
        """Save the FAISS index and metadata to disk."""
        if path is None:
            if self.index_path is None:
                raise ValueError("No path provided to save the index")
            path = self.index_path
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, path)
        
        # Save metadata
        metadata_path = self._get_metadata_path(path)
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
    
    def load_index(self, path: str) -> None:
        """Load the FAISS index and metadata from disk."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Index file not found: {path}")
        
        # Load FAISS index
        self.index = faiss.read_index(path)
        self.index_path = path
        
        # Load metadata
        metadata_path = self._get_metadata_path(path)
        if os.path.exists(metadata_path):
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
    
    def _get_metadata_path(self, index_path: str) -> str:
        """Get the path for the metadata file based on the index path."""
        return f"{index_path}.metadata"
    
    def get_vector_count(self) -> int:
        """Get the number of vectors in the index."""
        if self.index is None:
            return 0
        return self.index.ntotal
    
    def clear(self) -> None:
        """Clear all vectors and metadata from the index."""
        if self.index is not None:
            self.index.reset()
        self.metadata = []


class DocumentStore:
    """
    A higher-level document store that manages document chunks and their vector representations.
    """
    
    def __init__(self, index_dir: str = "indices", index_name: str = "default"):
        """
        Initialize the document store.
        
        Args:
            index_dir: Directory to store the index files
            index_name: Name of the index
        """
        os.makedirs(index_dir, exist_ok=True)
        self.index_path = os.path.join(index_dir, f"{index_name}.faiss")
        self.embedder = LocalEmbedder()
        # Initialize with default dimension, will be updated on first use
        self.vector_store = None
        self._initialized = False
    
    async def _initialize_vector_store(self):
        """Initialize the vector store with the correct embedding dimension."""
        if not self._initialized:
            # Get the embedding dimension from the embedder
            sample_embeddings = await self.embedder.generate_embeddings(["sample text"])
            embedding_dim = len(sample_embeddings[0])
            self.vector_store = FAISSVectorStore(self.index_path, dimension=embedding_dim)
            self._initialized = True
    
    async def add_documents(
        self, 
        texts: List[str], 
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Add document texts and their metadata to the store.
        
        Args:
            texts: List of document texts
            metadatas: Optional list of metadata dictionaries
        """
        # Initialize vector store if not already done
        await self._initialize_vector_store()
            
        if metadatas is None:
            metadatas = [{} for _ in texts]
            
        if len(texts) != len(metadatas):
            raise ValueError("Length of texts and metadatas must be equal")
        
        # Add text to metadata
        for i, text in enumerate(texts):
            if 'text' not in metadatas[i]:
                metadatas[i]['text'] = text
        
        # Generate embeddings for the texts
        try:
            # Generate embeddings and convert to numpy array
            embeddings = await self.embedder.generate_embeddings(texts)
            if not embeddings or len(embeddings) == 0:
                raise ValueError("No embeddings were generated")
                
            vectors = np.array(embeddings, dtype=np.float32)
            
            # Verify the shape of the vectors
            if len(vectors.shape) != 2 or vectors.shape[1] == 0:
                raise ValueError(f"Invalid embedding shape: {vectors.shape}")
            
            # Verify metadata length matches number of vectors
            if len(metadatas) != len(vectors):
                raise ValueError(f"Mismatch between number of embeddings ({len(vectors)}) and metadatas ({len(metadatas)})")
            
            # Add to vector store
            self.vector_store.add_vectors(vectors, metadatas)
        except Exception as e:
            error_msg = f"Error in add_documents: {str(e)}\n"
            error_msg += f"Number of texts: {len(texts)}\n"
            error_msg += f"Number of metadatas: {len(metadatas)}\n"
            if 'embeddings' in locals():
                error_msg += f"Number of embeddings: {len(embeddings) if embeddings else 0}\n"
                if embeddings and len(embeddings) > 0:
                    error_msg += f"First embedding length: {len(embeddings[0]) if embeddings[0] else 0}\n"
            if 'vectors' in locals():
                error_msg += f"Vectors shape: {vectors.shape if hasattr(vectors, 'shape') else 'N/A'}\n"
            raise ValueError(error_msg)
    
    async def similarity_search(
        self, 
        query: str, 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents to the query.
        
        Args:
            query: The search query
            k: Number of results to return
            
        Returns:
            List of metadata dictionaries for the top-k results
        """
        # Initialize vector store if not already done
        await self._initialize_vector_store()
        
        # Generate embedding for the query
        try:
            query_embedding = await self.embedder.generate_embeddings([query])
            query_vector = np.array(query_embedding[0], dtype=np.float32)
            
            # Perform the search
            results, _ = self.vector_store.similarity_search(query_vector, k)
            return results
        except Exception as e:
            raise ValueError(f"Error performing similarity search: {str(e)}")
    
    async def save(self) -> None:
        """Save the index to disk."""
        if not self._initialized:
            await self._initialize_vector_store()
        self.vector_store.save_index()
    
    async def clear(self) -> None:
        """Clear all documents from the store."""
        if not self._initialized:
            await self._initialize_vector_store()
        self.vector_store.clear()
    
    async def get_document_count(self) -> int:
        """Get the total number of document chunks in the store."""
        if not self._initialized:
            # If not initialized, check if there's an existing index
            if os.path.exists(self.index_path):
                await self._initialize_vector_store()
            else:
                return 0
        return self.vector_store.get_vector_count()
