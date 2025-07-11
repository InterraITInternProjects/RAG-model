from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import re
from .chunks_model import DocumentChunkResponse 


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
