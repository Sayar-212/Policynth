import google.generativeai as genai
from typing import List
from config.settings import settings
from models.schemas import RetrievalResult

class LLMService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    def generate_answer(self, question: str, context_chunks: List[RetrievalResult]) -> str:
        """Generate answer using Gemini with enhanced context handling"""
        if not context_chunks:
            return "No relevant information found in the document."

        # Sort chunks by relevance and prepare context
        sorted_chunks = sorted(context_chunks, key=lambda x: x.score, reverse=True)

        # Format chunks with clear separation
        context_text = "\n\n---\n\n".join([
            f"RELEVANT SECTION {i+1} (Score: {result.score:.3f}):\n{result.chunk.text.strip()}" 
            for i, result in enumerate(sorted_chunks)
        ])

        prompt = self._create_prompt(question, context_text)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=512
                )
            )
            return response.text.strip() if response.text else "Unable to generate response from the provided context."
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def _create_prompt(self, question: str, context: str) -> str:
        """Create focused prompt for accurate document analysis"""
        return f"""You are an expert insurance policy analyst. Answer the question using ONLY the provided context.

DOCUMENT CONTEXT:
{context}

QUESTION: {question}

INSTRUCTIONS:
- Search through ALL provided sections carefully
- Extract exact numbers, periods, percentages, and conditions
- If information spans multiple sections, combine them logically
- Quote specific policy terms when relevant
- If the exact answer isn't in the context, state what related information is available
- Be precise with technical insurance terms

ANSWER:"""