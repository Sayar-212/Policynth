import fitz  # PyMuPDF
import docx
import requests
import tempfile
import os
import re
from typing import List, Dict, Any
from models.schemas import DocumentChunk
from config.settings import settings
import uuid
import hashlib

class DocumentProcessor:
    def __init__(self):
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        self.heading_patterns = [
            re.compile(r'^[A-Z][A-Z\s]{5,}$'),  # ALL CAPS HEADINGS
            re.compile(r'^\d+\.\d+\s+[A-Z]'),    # Numbered sections
            re.compile(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*:$'),  # Title Case with colon
        ]
    
    async def download_document(self, blob_url: str) -> str:
        """Download document from blob URL to temporary file"""
        try:
            response = requests.get(blob_url, stream=True)
            response.raise_for_status()
            
            # Create temporary file
            suffix = '.pdf' if 'pdf' in blob_url.lower() else '.docx'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                return tmp_file.name
        except Exception as e:
            raise Exception(f"Failed to download document: {str(e)}")
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF using PyMuPDF"""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                page_text = page.get_text()
                # Clean common PDF artifacts
                page_text = re.sub(r'\n{3,}', '\n\n', page_text)  # Remove excessive newlines
                page_text = re.sub(r'\s{2,}', ' ', page_text)     # Remove excessive spaces
                text += page_text + "\n"
            doc.close()
            return text
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")
    
    def detect_document_structure(self, text: str) -> List[Dict[str, Any]]:
        """Detect document structure intelligently"""
        lines = text.split('\n')
        sections = []
        current_section = {'type': 'content', 'content': [], 'level': 0}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line is a heading
            is_heading = False
            heading_level = 0
            
            for pattern in self.heading_patterns:
                if pattern.match(line):
                    is_heading = True
                    if line.isupper():
                        heading_level = 1
                    elif re.match(r'^\d+\.', line):
                        heading_level = 2
                    else:
                        heading_level = 3
                    break
            
            if is_heading:
                if current_section['content']:
                    sections.append(current_section)
                current_section = {'type': 'heading', 'content': [line], 'level': heading_level, 'heading_text': line}
            else:
                current_section['content'].append(line)
        
        if current_section['content']:
            sections.append(current_section)
            
        return sections
    
    def create_semantic_chunks(self, text: str) -> List[DocumentChunk]:
        """STUNNER Semantic Chunking - intelligent clause-based chunking with overlap"""
        # Multi-level splitting for better semantic boundaries
        sections = self._split_by_semantic_boundaries(text)
        chunks = []
        
        for section in sections:
            section_chunks = self._create_overlapping_chunks(section)
            chunks.extend(section_chunks)
        
        print(f"🎯 Created {len(chunks)} semantic chunks with intelligent boundaries")
        
        # Print enhanced statistics
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk.metadata.get('type', 'unknown')
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        print(f"📊 Enhanced chunk distribution: {dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True))}")
        return chunks
    
    def _split_by_semantic_boundaries(self, text: str) -> List[Dict]:
        """Split text by semantic boundaries (headings, clauses, paragraphs)"""
        lines = text.split('\n')
        sections = []
        current_section = {'text': '', 'heading': '', 'type': 'content'}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect headings and section breaks
            if (line.isupper() and len(line) > 10) or \
               re.match(r'^\d+\.\s+[A-Z]', line) or \
               re.match(r'^[A-Z][A-Z\s]{10,}$', line) or \
               line.endswith(':') and len(line.split()) <= 5:
                
                # Save previous section
                if current_section['text'].strip():
                    sections.append(current_section)
                
                # Start new section
                current_section = {
                    'text': line,
                    'heading': line,
                    'type': 'heading'
                }
            else:
                current_section['text'] += '\n' + line
        
        # Add final section
        if current_section['text'].strip():
            sections.append(current_section)
        
        return sections
    
    def _create_overlapping_chunks(self, section: Dict) -> List[DocumentChunk]:
        """Create overlapping chunks within a section for better context"""
        text = section['text']
        sentences = self._split_into_sentences(text)
        chunks = []
        
        chunk_size = 200  # words per chunk
        overlap_size = 50  # overlap words
        
        current_chunk = []
        current_words = 0
        
        for sentence in sentences:
            sentence_words = len(sentence.split())
            
            # If adding sentence exceeds limit, create chunk
            if current_words + sentence_words > chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                
                if len(chunk_text.split()) >= 50:  # Minimum meaningful size
                    chunk = self._create_chunk_with_metadata(chunk_text, section, len(chunks))
                    chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk, overlap_size)
                current_chunk = overlap_sentences + [sentence]
                current_words = sum(len(s.split()) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_words += sentence_words
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text.split()) >= 50:
                chunk = self._create_chunk_with_metadata(chunk_text, section, len(chunks))
                chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences with smart boundary detection"""
        # Simple sentence splitting with common patterns
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_sentences(self, sentences: List[str], overlap_words: int) -> List[str]:
        """Get last few sentences for overlap based on word count"""
        overlap_sentences = []
        word_count = 0
        
        for sentence in reversed(sentences):
            sentence_words = len(sentence.split())
            if word_count + sentence_words <= overlap_words:
                overlap_sentences.insert(0, sentence)
                word_count += sentence_words
            else:
                break
        
        return overlap_sentences
    
    def _create_chunk_with_metadata(self, text: str, section: Dict, chunk_index: int) -> DocumentChunk:
        """Create chunk with rich metadata for better retrieval"""
        section_type = self.detect_section_type(text)
        
        return DocumentChunk(
            id=str(uuid.uuid4()),
            text=text,
            metadata={
                "source": "document",
                "section": section.get('heading', f"section_{chunk_index}")[:100],
                "type": section_type,
                "chunk_type": section.get('type', 'content'),
                "is_heading": section.get('type') == 'heading',
                "chunk_index": chunk_index,
                "word_count": len(text.split()),
                "has_numbers": bool(re.search(r'\d+', text)),
                "has_definitions": 'means' in text.lower() or 'defined as' in text.lower()
            }
        )
    
    def detect_section_type(self, text: str) -> str:
        """Enhanced section type detection for better metadata filtering"""
        text_lower = text.lower()
        
        # Priority-based detection
        if any(word in text_lower for word in ['definition', 'means', 'defined as', 'shall mean']):
            return 'definitions'
        elif any(word in text_lower for word in ['coverage', 'benefit', 'covered', 'insured', 'protection']):
            return 'coverage'
        elif any(word in text_lower for word in ['exclusion', 'excluded', 'not covered', 'does not cover']):
            return 'exclusions'
        elif any(word in text_lower for word in ['limit', 'maximum', 'minimum', 'deductible', 'amount']):
            return 'limits'
        elif any(word in text_lower for word in ['claim', 'procedure', 'process', 'submit']):
            return 'claims'
        elif any(word in text_lower for word in ['premium', 'payment', 'cost', 'fee']):
            return 'premiums'
        elif any(word in text_lower for word in ['condition', 'requirement', 'must', 'shall']):
            return 'conditions'
        else:
            return 'policy_clause'
    
    async def process_document(self, blob_url: str) -> List[DocumentChunk]:
        """Main method to process document and return chunks"""
        # Download document
        file_path = await self.download_document(blob_url)
        
        try:
            # Extract text based on file type
            if file_path.endswith('.pdf'):
                text = self.extract_text_from_pdf(file_path)
            elif file_path.endswith('.docx'):
                text = self.extract_text_from_docx(file_path)
            else:
                raise Exception("Unsupported file format")
            
            # Clean text and create semantic chunks
            text = self.clean_text(text)
            chunks = self.create_semantic_chunks(text)
            
            # Update metadata with source URL
            for chunk in chunks:
                chunk.metadata["source"] = blob_url
            
            return chunks
            
        finally:
            # Clean up temporary file
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = " ".join(text.split())
        # Remove special characters that might interfere
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\u2019', "'")  # Right single quotation mark
        text = text.replace('\u201c', '"')  # Left double quotation mark
        text = text.replace('\u201d', '"')  # Right double quotation mark
        return text