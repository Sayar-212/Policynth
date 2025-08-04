import faiss
import numpy as np
import json
import os
from typing import List, Dict, Any, Optional
from models.schemas import DocumentChunk, RetrievalResult
from config.settings import settings

class VectorStore:
    def __init__(self):
        """Initialize FAISS vector store"""
        self.dimension = 384  # all-MiniLM-L6-v2 dimension
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
        self.chunks_metadata = {}  # Store full chunk data
        self.index_path = settings.FAISS_INDEX_PATH
        self.metadata_path = settings.FAISS_METADATA_PATH
        
        # Load existing index if available
        self._load_index()
    
    def store_chunks(self, chunks: List[DocumentChunk]):
        """Store document chunks in FAISS index"""
        if not chunks:
            return
            
        # Clear existing data
        self.clear_index()
        
        vectors = []
        for chunk in chunks:
            if chunk.embedding:
                # Normalize for cosine similarity
                embedding = np.array(chunk.embedding, dtype=np.float32)
                embedding = embedding / np.linalg.norm(embedding)
                vectors.append(embedding)
                
                # Store full chunk data
                self.chunks_metadata[len(vectors) - 1] = {
                    "id": chunk.id,
                    "text": chunk.text,
                    "metadata": chunk.metadata
                }
        
        if vectors:
            # Add to FAISS index
            vectors_array = np.array(vectors, dtype=np.float32)
            self.index.add(vectors_array)
            print(f"Stored {len(vectors)} chunks in FAISS index")
            
            # Print metadata distribution for debugging
            types = {}
            for chunk_data in self.chunks_metadata.values():
                chunk_type = chunk_data["metadata"].get("type", "unknown")
                types[chunk_type] = types.get(chunk_type, 0) + 1
            
            print(f"   Chunk types: {dict(sorted(types.items(), key=lambda x: x[1], reverse=True))}")
            
            # Save to disk
            self._save_index()
    
    def search_similar(self, query_embedding: List[float], top_k: int = 4, metadata_filter: Dict = None, debug: bool = False, query_text: str = None, query_intent: Dict = None) -> List[RetrievalResult]:
        """Enhanced search with better scoring and filtering"""
        try:
            if self.index.ntotal == 0:
                return []
            
            # Normalize query embedding
            query_vector = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
            query_vector = query_vector / np.linalg.norm(query_vector)
            
            # Search more candidates for better filtering
            search_k = min(settings.MAX_SEARCH_CANDIDATES, self.index.ntotal)
            scores, indices = self.index.search(query_vector, search_k)
            
            if debug:
                print(f"   Searched {search_k} candidates from {self.index.ntotal} total chunks")
            
            results = []
            filtered_count = 0
            
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:
                    continue
                    
                chunk_data = self.chunks_metadata.get(idx)
                if not chunk_data:
                    continue
                
                # Apply metadata filtering
                if metadata_filter and not self._matches_filter(chunk_data["metadata"], metadata_filter):
                    filtered_count += 1
                    continue
                
                # Advanced hybrid scoring with insurance-specific optimizations
                enhanced_score = self._calculate_enhanced_score(score, chunk_data["metadata"], query_text, chunk_data["text"], query_intent)
                
                # Apply similarity threshold
                if enhanced_score < settings.SIMILARITY_THRESHOLD:
                    continue
                
                chunk = DocumentChunk(
                    id=chunk_data["id"],
                    text=chunk_data["text"],
                    metadata=chunk_data["metadata"]
                )
                
                results.append(RetrievalResult(
                    chunk=chunk,
                    score=enhanced_score
                ))
            
            if debug and filtered_count > 0:
                print(f"   Filtered {filtered_count} chunks by metadata")
            
            # Sort by enhanced score and return top_k
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]
            
        except Exception as e:
            raise Exception(f"Failed to search vectors: {str(e)}")
    
    def _matches_filter(self, metadata: Dict, filter_dict: Dict) -> bool:
        """Check if metadata matches filter criteria"""
        for key, value in filter_dict.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
    
    def _calculate_enhanced_score(self, base_score: float, metadata: Dict, query_text: str = None, chunk_text: str = None, query_intent: Dict = None) -> float:
        """Advanced hybrid scoring for insurance policy retrieval"""
        score = base_score
        
        # Simple intent-based scoring
        if query_intent:
            intent_type = query_intent.get('intent_type', '')
            section_type = metadata.get('type', '')
            
            # Logical section matching
            if intent_type == 'definition' and section_type == 'definitions':
                score *= 1.8
            elif intent_type in ['specific_value', 'time_period'] and section_type in ['coverage', 'conditions', 'limits']:
                score *= 1.6
            elif intent_type == 'coverage_check' and section_type in ['coverage', 'benefits']:
                score *= 1.5
            elif intent_type == 'exclusion_check' and section_type == 'exclusions':
                score *= 1.7
            
            # Small boost for numeric content when asking for values
            if intent_type in ['specific_value', 'time_period', 'limits'] and metadata.get('has_numbers', False):
                score *= 1.3
        
        # 1. METADATA-BASED BOOSTING
        section_type = metadata.get('type', '')
        if section_type == 'definitions':
            score *= 1.6  # Highest priority for definitions
        elif section_type in ['coverage', 'limits', 'benefits']:
            score *= 1.4  # High priority for coverage info
        elif section_type in ['exclusions', 'conditions']:
            score *= 1.3  # Important for what's not covered
        elif section_type in ['claims', 'procedures']:
            score *= 1.2  # Process-related information
        
        # Content quality indicators
        if metadata.get('has_definitions', False):
            score *= 1.5
        if metadata.get('has_numbers', False):
            score *= 1.2  # Numbers often contain specific limits/periods
        if metadata.get('is_heading', False):
            score *= 1.1
        
        # 2. QUERY-SPECIFIC HYBRID BOOSTING
        if query_text and chunk_text:
            query_lower = query_text.lower()
            chunk_lower = chunk_text.lower()
            
            # Insurance-specific query patterns
            score = self._apply_insurance_query_boosts(score, query_lower, chunk_lower, section_type)
            
            # Keyword density scoring
            score = self._apply_keyword_density_boost(score, query_lower, chunk_lower)
            
            # Exact phrase matching
            score = self._apply_phrase_matching_boost(score, query_lower, chunk_lower)
        
        return score
    
    def _apply_insurance_query_boosts(self, score: float, query_lower: str, chunk_lower: str, section_type: str) -> float:
        """Apply insurance domain-specific query boosts"""
        
        # Definition queries
        if any(word in query_lower for word in ['definition', 'define', 'what is', 'meaning']):
            if 'means' in chunk_lower or 'definition' in chunk_lower:
                score *= 2.2
            if section_type == 'definitions':
                score *= 1.8
        
        # Coverage/benefit queries
        if any(word in query_lower for word in ['covered', 'coverage', 'benefit', 'include']):
            if any(word in chunk_lower for word in ['covered', 'coverage', 'benefit', 'include', 'pay', 'reimburse']):
                score *= 1.8
        
        # Exclusion queries
        if any(word in query_lower for word in ['excluded', 'exclusion', 'not covered', 'exception']):
            if any(word in chunk_lower for word in ['excluded', 'exclusion', 'not covered', 'exception', 'does not']):
                score *= 1.9
        
        # Time period queries
        if any(word in query_lower for word in ['days', 'months', 'years', 'period', 'duration']):
            if any(char.isdigit() for char in chunk_lower) and any(word in chunk_lower for word in ['days', 'months', 'years']):
                score *= 1.7
        
        # Limit/amount queries
        if any(word in query_lower for word in ['limit', 'amount', 'maximum', 'minimum', 'sum']):
            if any(word in chunk_lower for word in ['limit', 'amount', 'maximum', 'minimum', 'sum', 'usd', 'inr', '$']):
                score *= 1.6
        
        # Specific insurance terms
        insurance_terms = {
            'premium': ['premium', 'payment', 'cost'],
            'deductible': ['deductible', 'excess', 'co-pay'],
            'claim': ['claim', 'settlement', 'reimbursement'],
            'hospitalization': ['hospitalization', 'hospital', 'inpatient'],
            'pre-existing': ['pre-existing', 'pre existing', 'prior condition'],
            'waiting period': ['waiting period', 'waiting', 'exclusion period']
        }
        
        for query_term, chunk_terms in insurance_terms.items():
            if query_term in query_lower:
                if any(term in chunk_lower for term in chunk_terms):
                    score *= 1.5
        
        return score
    
    def _apply_keyword_density_boost(self, score: float, query_lower: str, chunk_lower: str) -> float:
        """Boost based on keyword density and relevance"""
        query_words = set(word for word in query_lower.split() if len(word) > 3)
        chunk_words = chunk_lower.split()
        
        if not query_words:
            return score
        
        # Calculate keyword match ratio
        matches = sum(1 for word in query_words if word in chunk_lower)
        match_ratio = matches / len(query_words)
        
        # Apply density-based boost
        if match_ratio >= 0.8:  # 80%+ keywords match
            score *= 1.4
        elif match_ratio >= 0.6:  # 60%+ keywords match
            score *= 1.2
        elif match_ratio >= 0.4:  # 40%+ keywords match
            score *= 1.1
        
        return score
    
    def _apply_phrase_matching_boost(self, score: float, query_lower: str, chunk_lower: str) -> float:
        """Boost for exact phrase matches"""
        # Extract meaningful phrases (2+ words)
        import re
        query_phrases = re.findall(r'\b\w+\s+\w+(?:\s+\w+)*\b', query_lower)
        
        for phrase in query_phrases:
            if len(phrase.split()) >= 2 and phrase in chunk_lower:
                score *= 1.3  # Exact phrase match bonus
        
        return score
    
    def get_chunk_by_text_search(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search chunks by text content for debugging"""
        results = []
        search_term_lower = search_term.lower()
        
        for idx, chunk_data in self.chunks_metadata.items():
            text = chunk_data.get("text", "").lower()
            if search_term_lower in text:
                results.append({
                    "index": idx,
                    "text": chunk_data.get("text", ""),
                    "metadata": chunk_data.get("metadata", {}),
                    "mentions": text.count(search_term_lower)
                })
        
        # Sort by number of mentions
        results.sort(key=lambda x: x["mentions"], reverse=True)
        return results[:limit]
    
    def clear_index(self):
        """Clear FAISS index but keep metadata for debugging"""
        self.index = faiss.IndexFlatIP(self.dimension)
        # Don't clear metadata - keep for debugging
        # self.chunks_metadata.clear()
        
        # Remove only index file, keep metadata
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        # Keep metadata file for debugging
        # if os.path.exists(self.metadata_path):
        #     os.remove(self.metadata_path)
    
    def _save_index(self):
        """Save FAISS index and metadata to disk"""
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.metadata_path, 'w') as f:
                json.dump(self.chunks_metadata, f)
        except Exception as e:
            print(f"Warning: Could not save index: {e}")
    
    def _load_index(self):
        """Load FAISS index and metadata from disk"""
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
                self.index = faiss.read_index(self.index_path)
                with open(self.metadata_path, 'r') as f:
                    # Convert string keys back to integers
                    metadata = json.load(f)
                    self.chunks_metadata = {int(k): v for k, v in metadata.items()}
                print(f"Loaded existing FAISS index with {self.index.ntotal} vectors")
        except Exception as e:
            print(f"Warning: Could not load existing index: {e}")
            self.index = faiss.IndexFlatIP(self.dimension)
            self.chunks_metadata = {}