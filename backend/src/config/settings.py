from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./app.db"

    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = [".pdf", ".txt", ".docx"]

    ALLOWED_FILE_TYPES = ['.pdf']
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    VECTOR_DB_DIR: str = "vector_db/indices"
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    SIMILARITY_THRESHOLD: float = 0.5
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
   
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"

settings = Settings()