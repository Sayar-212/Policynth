# Policynth

AI-powered insurance policy analysis and query system with advanced hybrid retrieval for accurate policy information extraction.

## Features

- 🏥 **Insurance-Focused**: Specialized for insurance policy analysis and queries
- 🔍 **Hybrid Search**: Advanced semantic + keyword + phrase matching
- 🤖 **LLM Integration**: Google Gemini API for intelligent response generation
- 🗄️ **Vector Database**: FAISS for efficient similarity search
- ⚡ **Fast API**: RESTful API with bearer token authentication
- 🎯 **Domain Intelligence**: Query intent analysis and insurance-specific scoring

## Architecture

```
Insurance Policy → Enhanced Processing → Semantic Chunks → Hybrid Search → Accurate Answers
       ↓                    ↓                ↓              ↓              ↓
   PDF/DOCX         Intelligent        Metadata      Query Intent    Contextual
   Extract          Chunking           Enhanced      Analysis        Responses
```

## Quick Start

### 1. Setup
```bash
git clone <your-repo>
cd Babachoda
python setup.py
```

### 2. Configure API Keys
Edit `.env` file:
```env
GEMINI_API_KEY=your_actual_gemini_api_key
PINECONE_API_KEY=your_actual_pinecone_api_key
PINECONE_ENVIRONMENT=gcp-starter
```

### 3. Run Application
```bash
python main.py
```

### 4. Test System
```bash
curl -X POST "http://localhost:8000/api/v1/hackrx/run" \
  -H "Authorization: Bearer 16bf0d621ee347f1a4b56589f04b1d3430e0b93e3a4faa109f64b4789400e9d8" \
  -H "Content-Type: application/json" \
  -d '{"documents": "https://example.com/policy.pdf", "questions": ["What is covered?"]}'```

## API Usage

### Endpoint
```
POST http://localhost:8000/api/v1/hackrx/run
Authorization: Bearer 16bf0d621ee347f1a4b56589f04b1d3430e0b93e3a4faa109f64b4789400e9d8
```

### Request Format
```json
{
    "documents": "https://hackrx.blob.core.windows.net/assets/policy.pdf",
    "questions": [
        "What is the grace period for premium payment?",
        "What is the waiting period for pre-existing diseases?"
    ]
}
```

### Response Format
```json
{
    "answers": [
        "A grace period of thirty days is provided for premium payment...",
        "There is a waiting period of thirty-six (36) months for pre-existing diseases..."
    ]
}
```

## Project Structure

```
├── config/
│   └── settings.py          # Configuration management
├── models/
│   └── schemas.py           # Pydantic models
├── services/
│   ├── document_processor.py   # PDF/DOCX processing
│   ├── embedding_service.py    # Text embeddings
│   ├── vector_store.py        # Pinecone operations
│   ├── llm_service.py         # Gemini API integration
│   └── query_engine.py        # Main orchestration
├── main.py                  # FastAPI application
├── test_client.py          # Testing script
├── setup.py               # Setup automation
├── requirements.txt       # Dependencies
├── .env                  # Environment variables
└── README.md            # Documentation
```

## Key Components

### Document Processor
- Downloads documents from blob URLs
- Extracts text from PDF/DOCX formats
- Chunks text with intelligent overlap
- Cleans and normalizes content

### Embedding Service
- Uses sentence-transformers (all-MiniLM-L6-v2)
- Generates 384-dimensional embeddings
- Optimized for CPU processing
- No API costs

### Vector Store
- Pinecone vector database integration
- Cosine similarity search
- Metadata storage for context
- Batch processing for efficiency

### LLM Service
- Google Gemini API integration
- Structured prompting for accuracy
- Context-aware response generation
- Error handling and fallbacks

## API Keys Setup

### Google Gemini API
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create new API key
3. Add to `.env` file

### Pinecone
1. Sign up at [Pinecone](https://www.pinecone.io/)
2. Create new project
3. Get API key and environment
4. Add to `.env` file

## Performance Optimization

- **CPU Optimized**: Uses sentence-transformers for local embeddings
- **Memory Efficient**: Streaming document processing
- **Batch Processing**: Optimized vector operations
- **Caching**: Reuses embeddings when possible

## Testing

The system includes comprehensive testing:
- Document processing validation
- Embedding generation tests
- Vector search accuracy
- End-to-end API testing

## Troubleshooting

### Common Issues

1. **API Key Errors**: Verify keys in `.env` file
2. **Pinecone Connection**: Check environment and index name
3. **Memory Issues**: Reduce chunk size in settings
4. **PDF Processing**: Install system dependencies for PyMuPDF

### Debug Mode
Set environment variable for detailed logging:
```bash
export PYTHONPATH=.
export DEBUG=True
python main.py
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## License

MIT License - see LICENSE file for details