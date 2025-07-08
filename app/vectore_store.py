import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle
import os
from typing import List, Tuple

class VectorStore:
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension) 
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.chunk_ids = []
        self.index_file = "faiss_index.bin"
        self.metadata_file = "chunk_metadata.pkl"
        
        self.load_index()
    
    def encode_text(self, text: str) -> np.ndarray:
        """Encode text to vector using sentence transformer"""
        embedding = self.model.encode([text])
        embedding = embedding / np.linalg.norm(embedding, axis=1, keepdims=True)
        return embedding.astype('float32')
    
    def add_chunks(self, texts: List[str], chunk_ids: List[int]):
        """Add text chunks to the vector store"""
        embeddings = []
        for text in texts:
            embedding = self.encode_text(text)
            embeddings.append(embedding[0])
        
        if embeddings:
            embeddings_array = np.array(embeddings)
            self.index.add(embeddings_array)
            self.chunk_ids.extend(chunk_ids)
            self.save_index()

    def delete_chunks(self, chunk_ids_to_delete: List[int]):
        """Delete chunks by chunk IDs - rebuilds the index without deleted chunks"""
        if not chunk_ids_to_delete:
            return
        
        indices_to_keep = []
        new_chunk_ids = []
        
        for i, chunk_id in enumerate(self.chunk_ids):
            if chunk_id not in chunk_ids_to_delete:
                indices_to_keep.append(i)
                new_chunk_ids.append(chunk_id)
        
        if not indices_to_keep:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.chunk_ids = []
        else:
            vectors_to_keep = []
            for i in indices_to_keep:
                vector = self.index.reconstruct(i)
                vectors_to_keep.append(vector)
            
            self.index = faiss.IndexFlatIP(self.dimension)
            if vectors_to_keep:
                vectors_array = np.array(vectors_to_keep)
                self.index.add(vectors_array)
            
            self.chunk_ids = new_chunk_ids
        
        self.save_index()
    
    def search(self, query: str, threshold: float = 0.5, k: int = 5) -> List[Tuple[int, float]]:
        """Search for similar chunks"""
        if self.index.ntotal == 0:
            return []
        
        query_embedding = self.encode_text(query)
        scores, indices = self.index.search(query_embedding, k)
        
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if score >= threshold:  
                chunk_id = self.chunk_ids[idx]
                results.append((chunk_id, float(score)))
        
        return results
    
    def save_index(self):
        """Save FAISS index and metadata"""
        faiss.write_index(self.index, self.index_file)
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.chunk_ids, f)
    
    def load_index(self):
        """Load FAISS index and metadata"""
        if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
            self.index = faiss.read_index(self.index_file)
            with open(self.metadata_file, 'rb') as f:
                self.chunk_ids = pickle.load(f)

vector_store = VectorStore()


print("Vector store initialized successfully")