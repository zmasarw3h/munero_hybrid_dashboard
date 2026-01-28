"""
Munero AI Platform - Backend API
FastAPI application with health checks and CORS configuration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import sqlite3
import os

from app.core.config import settings
from app.models import HealthResponse
from app.api import dashboard, chat, analyze

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered data analytics platform with natural language querying",
    debug=settings.DEBUG
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI Chat"])
app.include_router(analyze.router, prefix="/api/analyze", tags=["Driver Analysis"])


@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup"""
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📊 Database: {settings.DB_FILE}")
    print(f"🤖 LLM Model: {settings.OLLAMA_MODEL}")
    print(f"🔗 Ollama URL: {settings.OLLAMA_BASE_URL}")
    
    # Verify database exists
    if not os.path.exists(settings.DB_FILE):
        print(f"⚠️  WARNING: Database file not found at {settings.DB_FILE}")
        print("   Run: python scripts/ingest_data.py")
    else:
        # Test database connection
        try:
            conn = sqlite3.connect(settings.DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            print(f"✅ Database connected: {len(tables)} tables found")
        except Exception as e:
            print(f"❌ Database connection error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown"""
    print(f"🛑 Shutting down {settings.APP_NAME}")


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint to verify system status.
    
    Returns:
        - status: Application health status
        - timestamp: Current server time
        - database_connected: Whether SQLite database is accessible
        - llm_available: Whether Ollama LLM is reachable (placeholder for now)
    """
    # Check database connection
    db_connected = False
    try:
        if os.path.exists(settings.DB_FILE):
            conn = sqlite3.connect(settings.DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            db_connected = True
    except Exception as e:
        print(f"Health check - DB error: {e}")
    
    # TODO: Check Ollama availability (implement in next phase)
    llm_available = True  # Placeholder
    
    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        timestamp=datetime.now(),
        database_connected=db_connected,
        llm_available=llm_available
    )


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
