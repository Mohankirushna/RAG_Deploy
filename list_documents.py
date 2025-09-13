import os
import json
import faiss
import numpy as np
from pathlib import Path

# Path to the indices directory
INDICES_DIR = "/Users/projects/rag/indices"

def list_indices():
    """List all available FAISS indices"""
    print("Available FAISS indices:")
    for file in os.listdir(INDICES_DIR):
        if file.endswith('.faiss') and not file.endswith('.faiss.metadata'):
            index_name = file.replace('.faiss', '')
            metadata_file = os.path.join(INDICES_DIR, f"{index_name}.faiss.metadata")
            
            # Load metadata if exists
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    doc_count = len(metadata) if isinstance(metadata, list) else 0
                    print(f"- {index_name}: {doc_count} document chunks")
                except Exception as e:
                    print(f"- {index_name}: Error loading metadata - {str(e)}")
            else:
                print(f"- {index_name}: No metadata found")

def inspect_index(index_name):
    """Inspect a specific FAISS index"""
    index_path = os.path.join(INDICES_DIR, f"{index_name}.faiss")
    metadata_path = os.path.join(INDICES_DIR, f"{index_name}.faiss.metadata")
    
    if not os.path.exists(index_path):
        print(f"Error: Index '{index_name}' not found")
        return
    
    # Load the index
    try:
        index = faiss.read_index(index_path)
        print(f"\nIndex: {index_name}")
        print(f"Number of vectors: {index.ntotal}")
        print(f"Vector dimension: {index.d}")
    except Exception as e:
        print(f"Error loading index: {str(e)}")
        return
    
    # Load and display metadata
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            print("\nDocuments in index:")
            if isinstance(metadata, list):
                # Group by document_id
                docs = {}
                for i, meta in enumerate(metadata):
                    doc_id = meta.get('document_id', 'unknown')
                    if doc_id not in docs:
                        docs[doc_id] = {
                            'source': meta.get('source', 'unknown'),
                            'chunks': 0,
                            'first_chunks': []
                        }
                    docs[doc_id]['chunks'] += 1
                    if len(docs[doc_id]['first_chunks']) < 3:  # Show first 3 chunks
                        docs[doc_id]['first_chunks'].append(meta.get('text', '')[:100] + '...')
                
                # Print document summary
                for doc_id, info in docs.items():
                    print(f"\nDocument ID: {doc_id}")
                    print(f"Source: {info['source']}")
                    print(f"Number of chunks: {info['chunks']}")
                    print("Sample chunks:")
                    for i, chunk in enumerate(info['first_chunks'], 1):
                        print(f"  {i}. {chunk}")
            else:
                print("Metadata format not recognized")
                
        except Exception as e:
            print(f"Error loading metadata: {str(e)}")
    else:
        print("No metadata found for this index")

if __name__ == "__main__":
    print("RAG Document Inspector")
    print("====================")
    
    list_indices()
    
    while True:
        print("\nEnter index name to inspect (or 'q' to quit):")
        choice = input("> ").strip()
        
        if choice.lower() == 'q':
            break
            
        if choice:
            inspect_index(choice)
        else:
            print("Please enter a valid index name")
