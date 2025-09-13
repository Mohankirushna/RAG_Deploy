import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # API Configuration
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Model Configuration
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/embedding-001")
    GENERATION_MODEL: str = os.getenv("GENERATION_MODEL", "gemini-pro")
    
    # Text Processing
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "3"))
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # File Storage
    UPLOAD_FOLDER: str = "uploads"
    INDEX_FOLDER: str = "indices"
    
    class Config:
        case_sensitive = True

# Create settings instance
settings = Settings()

# Create necessary directories
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(settings.INDEX_FOLDER, exist_ok=True)
