import os
import re
from typing import List, Optional, Union, BinaryIO
from pathlib import Path
import PyPDF2
from docx import Document
import magic
from app.config import settings

class DocumentProcessor:
    """
    Handles document loading and text extraction from various file formats.
    """
    
    @staticmethod
    def detect_file_type(file_path: Union[str, BinaryIO]) -> str:
        """
        Detect the file type using python-magic.
        
        Args:
            file_path: Path to the file or file-like object
            
        Returns:
            str: Detected MIME type
        """
        mime = magic.Magic(mime=True)
        if hasattr(file_path, 'read'):
            # Handle file-like object
            file_path.seek(0)
            buffer = file_path.read(2048)
            file_path.seek(0)
            return mime.from_buffer(buffer)
        else:
            # Handle file path
            return mime.from_file(file_path)
    
    @staticmethod
    def extract_text_from_pdf(file_path: Union[str, BinaryIO]) -> str:
        """Extract text from PDF file."""
        try:
            pdf_reader = PyPDF2.PdfReader(file_path)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            raise ValueError(f"Error extracting text from PDF: {str(e)}")
    
    @staticmethod
    def extract_text_from_docx(file_path: Union[str, BinaryIO]) -> str:
        """Extract text from DOCX file."""
        try:
            doc = Document(file_path)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            raise ValueError(f"Error extracting text from DOCX: {str(e)}")
    
    @staticmethod
    def extract_text_from_txt(file_path: Union[str, BinaryIO]) -> str:
        """Extract text from TXT file."""
        try:
            if hasattr(file_path, 'read'):
                return file_path.read().decode('utf-8')
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Error reading text file: {str(e)}")
    
    def process_document(self, file_path: Union[str, BinaryIO], file_extension: Optional[str] = None) -> str:
        """
        Process a document and extract its text content.
        
        Args:
            file_path: Path to the file or file-like object
            file_extension: Optional file extension (e.g., '.pdf', '.docx', '.txt')
            
        Returns:
            str: Extracted text content
            
        Raises:
            ValueError: If the file cannot be processed
            IOError: If there's an error reading the file
        """
        try:
            mime_type = self.detect_file_type(file_path)
            
            # Determine the file type from MIME type or extension
            if 'pdf' in mime_type or (file_extension and file_extension.lower() == '.pdf'):
                return self.extract_text_from_pdf(file_path)
            elif 'word' in mime_type or 'vnd.openxmlformats-officedocument.wordprocessingml.document' in mime_type or \
                 (file_extension and file_extension.lower() == '.docx'):
                return self.extract_text_from_docx(file_path)
            elif 'text/plain' in mime_type or (file_extension and file_extension.lower() == '.txt'):
                return self.extract_text_from_txt(file_path)
            else:
                raise ValueError(f"Unsupported file type: {mime_type}. Supported types: PDF, DOCX, TXT")
                
        except Exception as e:
            # Add more context to the error message
            error_msg = f"Error processing document: {str(e)}"
            if hasattr(file_path, 'name'):
                error_msg += f" (File: {file_path.name})"
            elif isinstance(file_path, str):
                error_msg += f" (File: {file_path})"
                
            if 'magic' in str(e).lower():
                error_msg += ". Please ensure libmagic is installed on your system."
                
            raise ValueError(error_msg) from e
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Input text to be chunked
            chunk_size: Maximum size of each chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List[str]: List of text chunks
        """
        if not text or len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # If we're at the end, just take what's left
            if end >= len(text):
                chunks.append(text[start:].strip())
                break
                
            # Find the nearest sentence or paragraph end
            last_period = text.rfind('. ', start, end)
            last_newline = text.rfind('\n', start, end)
            
            # Prefer splitting at paragraph breaks, then sentence boundaries
            if last_newline > start and (last_newline - start) > (chunk_size // 2):
                end = last_newline + 1
            elif last_period > start and (last_period - start) > (chunk_size // 2):
                end = last_period + 1
            
            chunks.append(text[start:end].strip())
            
            # Move the start position, accounting for overlap
            start = end - overlap
            if start <= 0:  # Prevent infinite loops with very small chunks
                start = end
        
        return chunks
