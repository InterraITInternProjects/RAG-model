from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import re


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

class DocumentResponse(BaseModel):
    user_id: int
    doc_size: int
    
    class Config:
        from_attributes = True

