from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import re

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator('email')
    def validate_email(cls, v):
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if len(v) > 50:
            raise ValueError('Username must be less than 50 characters')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class User(BaseModel):
    id: int
    username: str
    email: str
    user_created_at: datetime
    
    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    response_created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

class DocumentUpload(BaseModel):
    filename: str
    chunk_count: int

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        if not v.strip():
            raise ValueError('Filename cannot be empty')
        valid_extensions = ['.txt', '.pdf', '.docx', '.md']
        if not any(v.lower().endswith(ext) for ext in valid_extensions):
            raise ValueError(f'File must have one of these extensions: {", ".join(valid_extensions)}')
        return v

class DocumentResponse(BaseModel):
    doc_id: int  
    doc_filename: str 
    doc_upload_time: datetime
    chunk_count: int
    user_id: int
    doc_size: int
    
    class Config:
        from_attributes = True

class QueryRequest(BaseModel):
    question: str
    document_ids: Optional[List[int]] = None
    max_results: Optional[int] = Field(default=5, ge=1, le=20)

    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty')
        if len(v) > 1000:
            raise ValueError('Question must be less than 1000 characters')
        return v.strip()

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]  
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None

class DocumentChunk(BaseModel):
    chunk_id: int
    doc_id: int
    chunk_idx: int
    chunk_content: str
    
    class Config:
        from_attributes = True

class DocumentChunkResponse(BaseModel):
    chunk_id: int
    doc_id: int
    chunk_idx: int
    chunk_content: str
    similarity_score: Optional[float] = None
    
    class Config:
        from_attributes = True

class QueryResponse(BaseModel):
    chunks: List[DocumentChunkResponse]  
    total_chunks: int

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class QueryCreate(BaseModel):
    question: str

    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty')
        if len(v) > 1000:
            raise ValueError('Question must be less than 1000 characters')
        return v.strip()

class QueryHistory(BaseModel):
    q_id: int  
    user_id: int
    q_text: str  
    q_asked_at: datetime
    
    class Config:
        from_attributes = True

class QueryHistoryResponse(BaseModel):
    q_id: int  
    q_text: str  
    q_asked_at: datetime
    
    class Config:
        from_attributes = True


print("Models module loaded successfully")