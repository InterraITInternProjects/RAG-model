from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, PrimaryKeyConstraint, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import os
from ..config.database import Base


class Chunk(Base):
    __tablename__ = "chunks"
    chunk_id = Column(Integer, nullable=False)
    doc_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False)
    chunk_idx = Column(Integer, nullable=False)
    chunk_content = Column(Text, nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint('chunk_id', 'doc_id'),
    )

    document = relationship("Document", back_populates="chunks")
    questions_logs = relationship("QuestionsLogs", back_populates="chunk")

