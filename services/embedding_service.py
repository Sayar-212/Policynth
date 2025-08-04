from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
from config.settings import settings
import hashlib
import json

class EmbeddingService:
    def __init__(self):
        """Initialize with sentence-transformers for local embeddings"""
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = 384  # all-MiniLM-L6-v2 dimension
    
    def encode_texts(self, texts: List[str], metadatas: List[Dict[str, Any]] = None) -> List[List[float]]:
        """Generate embeddings using sentence-transformers with batching"""
        try:
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            raise Exception(f"Failed to generate embeddings: {str(e)}")
    
    def encode_single_text(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        try:
            embedding = self.model.encode([text], convert_to_tensor=False)[0]
            return embedding.tolist()
        except Exception as e:
            raise Exception(f"Failed to generate embedding: {str(e)}")