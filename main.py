from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.schemas import QueryRequest, QueryResponse
from services.query_engine import QueryEngine
import uvicorn

app = FastAPI(
    title="Policynth",
    description="AI-powered insurance policy analysis and query system",
    version="1.0.0"
)

# Security
security = HTTPBearer()
VALID_TOKEN = "16bf0d621ee347f1a4b56589f04b1d3430e0b93e3a4faa109f64b4789400e9d8"

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize query engine
query_engine = QueryEngine()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify bearer token"""
    if credentials.credentials != VALID_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

@app.post("/api/v1/hackrx/run", response_model=QueryResponse)
async def run_query(request: QueryRequest, token: str = Depends(verify_token)):
    """Main endpoint to process document queries"""
    try:
        response = await query_engine.process_query(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Policynth is running"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Policynth - AI Insurance Policy Analysis",
        "version": "1.0.0",
        "endpoints": {
            "query": "/api/v1/hackrx/run",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False  # Disable reload in production
    )