import fitz  # PyMuPDF
from typing import List
import io
import logging

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file using PyMuPDF (fitz) with detailed logging"""
    logger = logging.getLogger(__name__)
    try:
        text = ""
        with fitz.open(stream=file_content, filetype="pdf") as doc:
            logger.info(f"PDF opened successfully. Number of pages: {doc.page_count}")
            for i, page in enumerate(doc):
                page_text = page.get_text()
                logger.info(f"Page {i+1}: Extracted {len(page_text)} characters.")
                if page_text:
                    text += page_text + "\n"
        logger.info(f"Total extracted text length: {len(text)}")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise ValueError(f"Error extracting text from PDF: {str(e)}")

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break
    return chunks

print("Text extraction and chunking utilities loaded successfully")