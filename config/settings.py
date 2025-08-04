import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    # FAISS settings
    FAISS_INDEX_PATH = "faiss_index.bin"
    FAISS_METADATA_PATH = "faiss_metadata.json"
    
    # Model settings
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS = 384
    CHUNK_SIZE = 300  # Optimized chunk size
    CHUNK_OVERLAP = 75   # Optimized overlap
    TOP_K_RETRIEVAL = 4  # Optimized for production
    
    # Enhanced retrieval settings
    SIMILARITY_THRESHOLD = 0.2  # Minimum similarity score
    MAX_SEARCH_CANDIDATES = 15  # Search more candidates for better filtering
    
    # API settings
    MAX_TOKENS = 4096
    TEMPERATURE = 0.1

settings = Settings()