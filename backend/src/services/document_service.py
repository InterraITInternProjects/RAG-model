from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from ..schema.models.users_model import UserCreate, UserLogin, UserResponse, TokenData, Token, User
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from utils.auth import create_access_token, verify_password, get_password_hash, verify_token, validate_password_strength, get_user_by_email, get_user, create_user, authenticate_user, get_current_user
from ..schema.documents import Document
from ..schema.chunks import Chunk
from ..utils.text_process import extract_text_from_pdf, chunk_text
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..config.settings import ALLOWED_FILE_TYPES, MAX_FILE_SIZE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, vector_store
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentService:
    async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
        try:
            if not any(file.filename.lower().endswith(ext) for ext in ALLOWED_FILE_TYPES):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Only {', '.join(ALLOWED_FILE_TYPES)} files are supported"
                )
            
            content = await file.read()
            
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413, 
                    detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
                )
            
            existing_doc = db.query(Document).filter(
                Document.user_id == current_user.user_id,
                Document.doc_filename == file.filename
            ).first()
            
            if existing_doc:
                raise HTTPException(
                    status_code=409,
                    detail="A document with this filename already exists"
                )
        
            try:
                text = extract_text_from_pdf(content)
                if not text.strip():
                    raise HTTPException(status_code=400, detail="PDF appears to be empty or unreadable")
            except ValueError as e:
                logger.error(f"PDF extraction failed for {file.filename}: {str(e)}")
                raise HTTPException(status_code=400, detail=f"PDF processing failed: {str(e)}")
            
            chunks = chunk_text(text)
            if not chunks:
                raise HTTPException(status_code=400, detail="No text chunks could be created from the document")
            document = Document(
                user_id=current_user.user_id,
                doc_filename=file.filename,
                doc_size=len(content),
            )
            db.add(document)
            db.commit()
            db.refresh(document)

            document.chunk_count = len(chunks)
            db.commit()
            db.refresh(document)

            chunk_objects = []
            chunk_texts = []
            for i, chunk_content in enumerate(chunks):
                chunk = Chunk(
                    chunk_id=i, 
                    doc_id=document.doc_id,
                    chunk_idx=i,
                    chunk_content=chunk_content
                )
                chunk_objects.append(chunk)
                chunk_texts.append(chunk_content)
            db.add_all(chunk_objects)
            db.commit()
            chunk_keys = [(chunk.chunk_id, chunk.doc_id) for chunk in chunk_objects]
            vector_store.add_chunks(chunk_texts, chunk_keys)
            logger.info(f"File uploaded successfully: {file.filename} by user {current_user.user_name}")
            return {
                "message": "File uploaded successfully", 
                "document_id": document.doc_id, 
                "chunks": len(chunks),
                "filename": file.filename
            }
            
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error during file upload: {str(e)}")
            raise HTTPException(status_code=500, detail="File upload failed")


    async def get_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE
    ):
        try:
            if page < 1:
                raise HTTPException(status_code=400, detail="Page must be >= 1")
            if page_size < 1 or page_size > MAX_PAGE_SIZE:
                raise HTTPException(status_code=400, detail=f"Page size must be between 1 and {MAX_PAGE_SIZE}")
            
            offset = (page - 1) * page_size
            
            documents = db.query(Document).filter(
                Document.user_id == current_user.user_id
            ).order_by(Document.doc_upload_time.desc()).offset(offset).limit(page_size).all()

            document_ids = [doc.doc_id for doc in documents]
            
            total_count = db.query(Document).filter(Document.user_id == current_user.user_id).count()
            
            return {
                "documents_id": document_ids,
                "documents": documents,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching documents: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch documents")
        
    
    async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
    ):
        try:
            document = db.query(Document).filter(
                Document.doc_id == document_id,  
                Document.user_id == current_user.user_id
            ).first()
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")
            chunks = db.query(Chunk).filter(Chunk.doc_id == document_id).all()
            chunk_keys = [(chunk.chunk_id, chunk.doc_id) for chunk in chunks]
            if chunk_keys:
                vector_store.delete_chunks(chunk_keys)
            db.query(Chunk).filter(Chunk.doc_id == document_id).delete()
            db.delete(document)
            db.commit()
            logger.info(f"Document deleted: {document_id} by user {current_user.user_name}")
            return {"message": "Document deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting document: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to delete document")

