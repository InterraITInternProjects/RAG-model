from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, PrimaryKeyConstraint, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import os
from backend.src.config.database import Base


class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, nullable=False)
    user_email = Column(String, nullable=False)
    user_password = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    user_created_at = Column(DateTime, default=datetime.utcnow)
   
    documents = relationship("Document", back_populates="user")
    questions_logs = relationship("QuestionsLogs", back_populates="user")