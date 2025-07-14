from fastapi import FastAPI, Depends, HTTPException
from ..schema.models.question_logs_model import QueryRequest, QueryResponse, ErrorResponse, QueryCreate, QueryHistory, QueryHistoryResponse
from ..schema.models.users_model import User
from ..schema.models.chunks_model import DocumentChunkResponse, DocumentChunk
from ..schema.question_logs import QuestionsLogs
from ..schema.chunks import Chunk
from datetime import datetime, timedelta
from sqlalchemy import tuple_
from utils.auth import get_current_user
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..config.settings import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, vector_store
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatService:
    async def query_documents(
    query: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
    ):
        try:
            if not query.question.strip():
                raise HTTPException(status_code=400, detail="Query cannot be empty")
            
            if len(query.question) > 1000:
                raise HTTPException(status_code=400, detail="Query too long (max 1000 characters)")
            
            results = vector_store.search(query.question, threshold=0.5, k=5)
            
            if not results:
                logger.info(f"No results found for query: {query.question}")
                query_log = QuestionsLogs(
                    user_id=current_user.user_id,
                    q_text=query.question,
                    ans_text="No relevant chunks found"
                )
                db.add(query_log)
                db.commit()
                return QueryResponse(chunks=[], total_chunks=0)
            
            chunk_keys = [key for key, _ in results]  
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
                        chunk_content=chunk.chunk_content,
                        similarity_score=score_map[key]
                    )   
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
    
    
    async def get_queries(
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
            
            queries = db.query(QuestionsLogs).filter(
                QuestionsLogs.user_id == current_user.user_id
            ).order_by(QuestionsLogs.q_asked_at.desc()).offset(offset).limit(page_size).all()
            
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

char_service = ChatService()   
