from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import re


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