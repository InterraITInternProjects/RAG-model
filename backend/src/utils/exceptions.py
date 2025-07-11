class RAGException(Exception):
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class AuthenticationError(RAGException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR")

class DocumentProcessingError(RAGException):
    def __init__(self, message: str = "Document processing failed"):
        super().__init__(message, "DOC_PROCESSING_ERROR")

class VectorSearchError(RAGException):
    def __init__(self, message: str = "Vector search failed"):
        super().__init__(message, "VECTOR_SEARCH_ERROR")

class ValidationError(RAGException):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, "VALIDATION_ERROR")

class FileProcessingError(RAGException):
    def __init__(self, message: str = "File processing failed"):
        super().__init__(message, "FILE_PROCESSING_ERROR")

class EmbeddingError(RAGException):
    def __init__(self, message: str = "Embedding generation failed"):
        super().__init__(message, "EMBEDDING_ERROR")