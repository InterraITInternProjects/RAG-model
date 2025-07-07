# backend/app/database.py

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, nullable=False)
    user_email = Column(String, nullable=False)
    user_password = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    # Relationships
    documents = relationship("Document", back_populates="user")
    questions_logs = relationship("QuestionsLogs", back_populates="user")

class Document(Base):
    __tablename__ = "documents"
    doc_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    doc_filename = Column(String, nullable=False)
    doc_size = Column(Integer, nullable=False)
    doc_upload_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"
    chunk_id = Column(Integer, nullable=False)
    doc_id = Column(Integer, ForeignKey("documents.doc_id"), nullable=False)
    chunk_idx = Column(Integer, nullable=False)
    chunk_content = Column(Text, nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint('chunk_id', 'doc_id'),
    )
    # Relationships
    document = relationship("Document", back_populates="chunks")
    questions_logs = relationship("QuestionsLogs", back_populates="chunk")

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
        ForeignKey(['chunk_id', 'chunk_doc_id'], ['chunks.chunk_id', 'chunks.doc_id']),
    )
    # Relationships
    user = relationship("User", back_populates="questions_logs")
    chunk = relationship("Chunk", back_populates="questions_logs")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)

# Explicitly export the classes and functions to make them importable from app.database
__all__ = ["User", "Document", "Chunk", "QuestionsLogs", "get_db", "init_db"]

print("Database module loaded successfully")