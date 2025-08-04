from typing import List, Dict, Any
from services.document_processor import DocumentProcessor
from services.embedding_service import EmbeddingService
from services.vector_store import VectorStore
from services.llm_service import LLMService

from models.schemas import QueryRequest, QueryResponse
from config.settings import settings
import google.generativeai as genai
import re
import json

class QueryEngine:
    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.llm_service = LLMService()
        
        # Initialize lightweight LLM for intent analysis
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.intent_analyzer = genai.GenerativeModel('gemini-1.5-flash')

    
    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """Main method to process document and answer questions"""
        import time
        start_time = time.time()
        
        try:
            # Step 1: Process document
            print("Processing document...")
            chunks = await self.doc_processor.process_document(request.documents)
            print(f"Created {len(chunks)} semantic chunks")
            
            # Step 2: Generate embeddings for chunks with metadata context
            print("Generating embeddings with context...")
            texts = [chunk.text for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]
            embeddings = self.embedding_service.encode_texts(texts, metadatas)
            
            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
            
            # Step 3: Clear existing data and store in vector database
            print("Storing in vector database...")
            self.vector_store.clear_index()
            self.vector_store.store_chunks(chunks)
            
            # Step 4: Process each question
            print(f"Processing {len(request.questions)} questions...")
            answers = []
            for i, question in enumerate(request.questions, 1):
                print(f"   Question {i}/{len(request.questions)}: Processing...")
                answer = await self._answer_question(question)
                answers.append(answer)
                print(f"   Question {i} completed")
            
            total_time = time.time() - start_time
            print(f"\nCOMPLETED: {len(chunks)} chunks processed, {len(answers)} answers generated in {total_time:.2f}s")
            

            
            # Clear FAISS index after processing (but keep metadata for debugging)
            self.vector_store.clear_index()
            print("FAISS index cleared (metadata preserved for debugging)")
            
            return QueryResponse(answers=answers)
            
        except Exception as e:
            raise Exception(f"Failed to process query: {str(e)}")
    
    async def _analyze_query_intent_smart(self, question: str) -> Dict[str, Any]:
        """Use lightweight LLM to intelligently analyze query intent"""
        try:
            prompt = f"""Analyze this insurance policy question and classify the user's intent:

Question: "{question}"

Classify into ONE of these categories:
- "definition" - asking what something means or is ("What is grace period?", "Define deductible")
- "specific_value" - asking for exact numbers, amounts, time periods ("How many days?", "What is the amount?", "How long is the waiting period?")
- "coverage_check" - asking what is covered or included ("Is X covered?", "Does this include Y?")
- "exclusion_check" - asking what is NOT covered ("What is excluded?", "Is X not covered?")
- "time_period" - asking about durations, waiting periods, grace periods ("How long?", "What is the waiting period?")
- "limits" - asking about maximum amounts, limits, caps ("What is the maximum?", "What are the limits?")

Return ONLY this JSON format:
{{
    "intent_type": "one_of_the_categories_above",
    "looking_for": "what_user_wants",
    "expects_numbers": true_or_false,
    "key_concepts": ["main_insurance_terms_in_question"]
}}"""
            
            response = await self.intent_analyzer.generate_content_async(prompt)
            
            # Clean response and extract JSON
            response_text = response.text.strip()
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].strip()
            
            try:
                intent_data = json.loads(response_text)
                return intent_data
            except json.JSONDecodeError:
                return self._extract_query_intent_fallback(question)
                
        except Exception as e:
            print(f"      WARNING: LLM intent analysis failed, using fallback: {e}")
            return self._extract_query_intent_fallback(question)
    
    def _extract_query_intent_fallback(self, question: str) -> Dict[str, Any]:
        """Intelligent query intent analysis with priority-based classification"""
        question_lower = question.lower()
        
        # Extract key insurance terms and phrases
        key_terms = self._extract_insurance_key_terms(question_lower)
        
        intent = {
            "keywords": re.findall(r'\b\w+\b', question_lower),
            "query_type": "general",
            "priority_sections": [],
            "expected_content": [],
            "key_terms": key_terms,
            "expects_numbers": self._expects_numerical_answer(question_lower),
            "expects_definitions": self._expects_definition_answer(question_lower),
            "intent_confidence": 0.0
        }
        
        # PRIORITY 1: Specific insurance terms (highest priority)
        if any(term in question_lower for term in ['grace period', 'waiting period', 'cooling period']):
            intent.update({
                "query_type": "time_period",
                "priority_sections": ['conditions', 'coverage', 'definitions'],
                "expected_content": ['period', 'days', 'months', 'grace', 'waiting'],
                "intent_confidence": 0.95
            })
            
        elif any(term in question_lower for term in ['pre-existing', 'pre existing', 'ped']):
            intent.update({
                "query_type": "pre_existing",
                "priority_sections": ['conditions', 'exclusions', 'definitions'],
                "expected_content": ['pre-existing', 'months', 'waiting', 'period'],
                "intent_confidence": 0.95
            })
            
        elif any(term in question_lower for term in ['maternity', 'pregnancy', 'childbirth']):
            intent.update({
                "query_type": "maternity",
                "priority_sections": ['coverage', 'benefits', 'conditions'],
                "expected_content": ['maternity', 'pregnancy', 'months', 'covered'],
                "intent_confidence": 0.95
            })
            
        elif any(term in question_lower for term in ['deductible', 'co-pay', 'copay', 'excess']):
            intent.update({
                "query_type": "deductible",
                "priority_sections": ['limits', 'conditions'],
                "expected_content": ['deductible', 'excess', 'amount', 'percentage'],
                "intent_confidence": 0.95
            })
        
        # PRIORITY 2: Question structure analysis (medium priority)
        elif self._is_asking_for_specific_value(question_lower):
            if any(word in question_lower for word in ['days', 'months', 'years', 'period', 'duration']):
                intent.update({
                    "query_type": "time_period",
                    "priority_sections": ['coverage', 'conditions', 'limits'],
                    "expected_content": ['days', 'months', 'years', 'period'],
                    "intent_confidence": 0.85
                })
            elif any(word in question_lower for word in ['amount', 'limit', 'maximum', 'minimum', 'sum']):
                intent.update({
                    "query_type": "limits",
                    "priority_sections": ['limits', 'coverage'],
                    "expected_content": ['limit', 'maximum', 'up to', 'amount'],
                    "intent_confidence": 0.85
                })
            else:
                intent.update({
                    "query_type": "specific_value",
                    "priority_sections": ['coverage', 'limits'],
                    "expected_content": ['amount', 'limit', 'covered'],
                    "intent_confidence": 0.75
                })
        
        # PRIORITY 3: General categories (lower priority)
        elif any(word in question_lower for word in ['covered', 'coverage', 'benefit', 'include', 'does cover']):
            intent.update({
                "query_type": "coverage",
                "priority_sections": ['coverage', 'benefits'],
                "expected_content": ['covered', 'benefit', 'pay', 'reimburse'],
                "intent_confidence": 0.70
            })
            
        elif any(word in question_lower for word in ['excluded', 'exclusion', 'not covered', 'does not cover']):
            intent.update({
                "query_type": "exclusion",
                "priority_sections": ['exclusions'],
                "expected_content": ['excluded', 'not covered', 'exception'],
                "intent_confidence": 0.70
            })
        
        # PRIORITY 4: Definition queries (only if very explicit and no specific values asked)
        elif self._is_pure_definition_query(question_lower):
            intent.update({
                "query_type": "definition",
                "priority_sections": ['definitions'],
                "expected_content": ['means', 'defined as', 'refers to'],
                "intent_confidence": 0.60
            })
        
        return intent
    
    def _extract_insurance_key_terms(self, question_lower: str) -> List[str]:
        """Extract key insurance terms from question"""
        insurance_terms = [
            'grace period', 'waiting period', 'cooling period',
            'pre-existing', 'pre existing', 'maternity', 'pregnancy',
            'deductible', 'co-pay', 'copay', 'excess',
            'sum insured', 'coverage limit', 'room rent',
            'icu charges', 'hospitalization', 'outpatient',
            'cashless', 'reimbursement', 'claim settlement',
            'no claim discount', 'ncd', 'bonus'
        ]
        
        found_terms = []
        for term in insurance_terms:
            if term in question_lower:
                found_terms.append(term)
        
        return found_terms
    
    def _expects_numerical_answer(self, question_lower: str) -> bool:
        """Determine if question expects numerical answer"""
        numerical_indicators = [
            'how much', 'how many', 'what is the amount',
            'what is the limit', 'how long', 'duration',
            'period', 'days', 'months', 'years',
            'percentage', 'rate', 'cost', 'premium'
        ]
        return any(indicator in question_lower for indicator in numerical_indicators)
    
    def _expects_definition_answer(self, question_lower: str) -> bool:
        """Determine if question expects definition/explanation"""
        definition_indicators = [
            'what is', 'what does', 'define', 'definition',
            'meaning', 'explain', 'what are'
        ]
        return any(indicator in question_lower for indicator in definition_indicators)
    
    def _is_asking_for_specific_value(self, question_lower: str) -> bool:
        """Check if asking for specific values rather than definitions"""
        specific_value_patterns = [
            'what is the', 'how much is the', 'what\'s the',
            'how many', 'how long is the', 'what are the limits'
        ]
        return any(pattern in question_lower for pattern in specific_value_patterns)
    
    def _is_pure_definition_query(self, question_lower: str) -> bool:
        """Check if it's purely asking for definition (not specific values)"""
        # Only consider it a definition query if it starts with definition words
        # AND doesn't ask for specific values
        starts_with_definition = question_lower.startswith(('what is', 'define', 'what does', 'meaning of'))
        asks_for_values = any(word in question_lower for word in ['amount', 'limit', 'period', 'days', 'months'])
        
        return starts_with_definition and not asks_for_values

    async def _answer_question(self, question: str) -> str:
        """Answer individual question using enhanced RAG"""
        try:
            # Generate embedding for question
            question_embedding = self.embedding_service.encode_single_text(question)

            # Intelligent query intent analysis using LLM
            query_intent = await self._analyze_query_intent_smart(question)
            
            relevant_chunks = self.vector_store.search_similar(
                question_embedding,
                top_k=settings.TOP_K_RETRIEVAL,
                query_text=question,
                query_intent=query_intent
            )

            # Clean output - show retrieved chunks with key info
            intent_type = query_intent.get('intent_type', 'general')
            looking_for = query_intent.get('looking_for', 'information')
            print(f"      Intent: {intent_type} - {looking_for}")
            print(f"      Retrieved {len(relevant_chunks)} chunks:")
            for i, chunk in enumerate(relevant_chunks, 1):
                chunk_preview = chunk.chunk.text[:60].replace('\n', ' ') + "..."
                print(f"         {i}. {chunk.score:.3f} | {chunk.chunk.metadata.get('type', 'unknown')} | {chunk_preview}")
            


            # Use retrieved chunks for LLM
            llm_chunks = relevant_chunks
            
            # Generate answer using LLM
            answer = self.llm_service.generate_answer(question, llm_chunks)

            return answer

        except Exception as e:
            return f"Error answering question: {str(e)}"
    