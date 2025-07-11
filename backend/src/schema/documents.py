from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, PrimaryKeyConstraint, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import os
from backend.src.config.database import Base


class Document(Base):
    __tablename__ = "documents"
    doc_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    doc_filename = Column(String, nullable=False)
    doc_size = Column(Integer, nullable=False)
    doc_upload_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    user = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")