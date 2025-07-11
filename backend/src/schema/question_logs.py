from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, PrimaryKeyConstraint, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import os
from backend.src.config.database import Base


class QuestionsLogs(Base):
    __tablename__ = "questions_logs"
    q_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    q_text = Column(Text, nullable=False)
    q_asked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    chunk_id = Column(Integer, nullable=True)  
    chunk_doc_id = Column(Integer, nullable=True)
    ans_text = Column(Text)
    ans_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        ForeignKeyConstraint(['chunk_id', 'chunk_doc_id'], ['chunks.chunk_id', 'chunks.doc_id']),
    )

    user = relationship("User", back_populates="questions_logs")
    chunk = relationship("Chunk", back_populates="questions_logs")