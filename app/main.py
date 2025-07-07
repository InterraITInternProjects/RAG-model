# backend/app/main.py

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import tuple_  # Add this import at the top with other imports
from datetime import timedelta
from typing import List, Optional
import os
import logging
from dotenv import load_dotenv

from app.database import init_db, get_db, User, Document, Chunk, QuestionsLogs
from app.models import UserCreate, UserLogin, Token, QueryRequest, QueryResponse, DocumentChunkResponse, DocumentResponse, QueryHistoryResponse
from app.auth import (
    authenticate_user, create_access_token, get_current_user, 
    get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES, create_user,
    validate_password_strength, get_user, get_user_by_email
)
from app.vectore_store import vector_store
from app.utils import extract_text_from_pdf, chunk_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_FILE_TYPES = ['.pdf']
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

app = FastAPI(title="RAG Application API", version="1.0.0")

# CORS middleware - more flexible configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    try:
        # Initialize database
        init_db()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

@app.post("/register", response_model=Token)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # Validate password strength
        is_valid, error_message = validate_password_strength(user.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        # Check if user exists
        existing_user = get_user(db, user.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        existing_email = get_user_by_email(db, user.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user with salted password
        db_user = create_user(db, user.username, user.email, user.password)
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        logger.info(f"New user registered: {user.username}")
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error during registration: {str(e)}")
        raise HTTPException(status_code=400, detail="Registration failed due to data conflict")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            logger.warning(f"Failed login attempt for username: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.user_name}, expires_delta=access_token_expires
        )
        
        logger.info(f"Successful login for user: {user.user_name}")
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Validate current password
        from app.auth import verify_password
        if not verify_password(current_password, current_user.user_password, current_user.salt):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Validate new password strength
        is_valid, error_message = validate_password_strength(new_password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        # Update password
        from app.auth import update_user_password
        if update_user_password(db, current_user, new_password):
            logger.info(f"Password changed for user: {current_user.user_name}")
            return {"message": "Password changed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update password")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        raise HTTPException(status_code=500, detail="Password change failed")

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Validate file type
        if not any(file.filename.lower().endswith(ext) for ext in ALLOWED_FILE_TYPES):
            raise HTTPException(
                status_code=400, 
                detail=f"Only {', '.join(ALLOWED_FILE_TYPES)} files are supported"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Check for duplicate files (by filename and user)
        existing_doc = db.query(Document).filter(
            Document.user_id == current_user.user_id,
            Document.doc_filename == file.filename
        ).first()
        
        if existing_doc:
            raise HTTPException(
                status_code=409,
                detail="A document with this filename already exists"
            )
        
        # Extract text from PDF
        try:
            text = extract_text_from_pdf(content)
            if not text.strip():
                raise HTTPException(status_code=400, detail="PDF appears to be empty or unreadable")
        except ValueError as e:
            logger.error(f"PDF extraction failed for {file.filename}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"PDF processing failed: {str(e)}")
        
        # Create chunks
        chunks = chunk_text(text)
        if not chunks:
            raise HTTPException(status_code=400, detail="No text chunks could be created from the document")
        document = Document(
            user_id=current_user.user_id,
            doc_filename=file.filename,
            doc_size=len(content),
            #chunk_count=len(chunks)
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
                chunk_id=i,  # composite key: chunk_id per doc
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

@app.post("/query", response_model=QueryResponse)
async def query_documents(
    query: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Validate query
        if not query.question.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if len(query.question) > 1000:
            raise HTTPException(status_code=400, detail="Query too long (max 1000 characters)")
        
        # Search in vector store
        results = vector_store.search(query.question, threshold=0.5, k=5)
        
        if not results:
            logger.info(f"No results found for query: {query.question}")
            # Log the query even if no results found
            query_log = QuestionsLogs(
                user_id=current_user.user_id,
                q_text=query.question,
                ans_text="No relevant chunks found"
            )
            db.add(query_log)
            db.commit()
            return QueryResponse(chunks=[], total_chunks=0)
        
        chunk_keys = [key for key, _ in results]  # key = (chunk_id, doc_id)
        chunks_data = db.query(Chunk).filter(
            tuple_(Chunk.chunk_id, Chunk.doc_id).in_(chunk_keys)
        ).all()
        chunks = []
        score_map = {key: score for key, score in results}
        for chunk in chunks_data:
            key = (chunk.chunk_id, chunk.doc_id)
            if key in score_map:
                chunk_response = DocumentChunkResponse(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    chunk_idx=chunk.chunk_idx,
                    chunk_content=chunk.chunk_content
                    similarity_score=score_map[key])   
                chunks.append(chunk_response)
        chunks.sort(key=lambda x: x.similarity_score, reverse=True)

        if chunks:
            best_chunk = chunks[0]
            query_log = QuestionsLogs(
                user_id=current_user.user_id,
                q_text=query.question,
                chunk_id=best_chunk.chunk_id,
                chunk_doc_id=best_chunk.doc_id,
                ans_text=f"Found {len(chunks)} relevant chunks"
            )
            db.add(query_log)
            db.commit()

        logger.info(f"Query processed successfully: {len(chunks)} chunks returned")
        return QueryResponse(chunks=chunks, total_chunks=len(chunks))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during query: {str(e)}")
        raise HTTPException(status_code=500, detail="Query processing failed")

@app.get("/documents")
async def get_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE
):
    try:
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be >= 1")
        if page_size < 1 or page_size > MAX_PAGE_SIZE:
            raise HTTPException(status_code=400, detail=f"Page size must be between 1 and {MAX_PAGE_SIZE}")
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get documents with pagination
        documents = db.query(Document).filter(
            Document.user_id == current_user.user_id
        ).order_by(Document.created_at.desc()).offset(offset).limit(page_size).all()
        
        # Get total count
        total_count = db.query(Document).filter(Document.user_id == current_user.user_id).count()
        
        return {
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

@app.get("/queries")
async def get_queries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE
):
    try:
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be >= 1")
        if page_size < 1 or page_size > MAX_PAGE_SIZE:
            raise HTTPException(status_code=400, detail=f"Page size must be between 1 and {MAX_PAGE_SIZE}")
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get queries with pagination
        queries = db.query(QuestionsLogs).filter(
            QuestionsLogs.user_id == current_user.user_id
        ).order_by(QuestionsLogs.q_asked_at.desc()).offset(offset).limit(page_size).all()
        
        # Get total count
        total_count = db.query(QuestionsLogs).filter(QuestionsLogs.user_id == current_user.user_id).count()
        
        return {
            "queries": queries,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching queries: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch queries")

@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        document = db.query(Document).filter(
            Document.doc_id == document_id,  # Fixed from Document.id
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

@app.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.user_id,
        "username": current_user.user_name,
        "email": current_user.user_email,
        "created_at": getattr(current_user, 'created_at', None)
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "RAG Application API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
