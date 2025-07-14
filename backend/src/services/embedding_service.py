from sentence_transformers import SentenceTransformer
import numpy as np
from ..config.settings import settings  
from typing import List

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def get_embeddings(self, text: List[str]) -> np.ndarray:
        embeddings = self.model.encode(text)
        return embeddings
    
    def get_single_embedding(self, text: str) -> np.ndarray:
        embedding = self.model.encode([text])
        return embedding[0]
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        dot_product = np.dot(embedding1, embedding2)
        norm_a = np.linalg.norm(embedding1)
        norm_b = np.linalg.norm(embedding2)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        somilarity = dot_product / (norm_a * norm_b)
        return float(somilarity)
    
embedding_service = EmbeddingService()