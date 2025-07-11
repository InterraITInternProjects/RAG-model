from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, ForeignKey, PrimaryKeyConstraint, ForeignKeyConstraint
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

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