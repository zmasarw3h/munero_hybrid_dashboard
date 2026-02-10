"""
Munero AI Platform - Backend API
FastAPI application with health checks and CORS configuration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from sqlalchemy import inspect, text
from sqlalchemy.engine.url import make_url

from app.core.config import settings
from app.core.database import engine
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

def _safe_db_url(db_uri: str) -> str:
    try:
        return make_url(db_uri).render_as_string(hide_password=True)
    except Exception:
        return "<invalid DB URI>"


@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup"""
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"🗄️  DB dialect: {settings.db_dialect}")
    print(f"🔗 DB URL: {_safe_db_url(settings.DB_URI)}")
    print(f"🌐 CORS origins: {settings.cors_origins_list}")
    print(f"🤖 LLM provider: {settings.LLM_PROVIDER}")
    print(f"🤖 LLM model: {settings.LLM_MODEL}")
    print(f"🔗 LLM base URL: {settings.LLM_BASE_URL}")
    print(f"🔐 LLM key configured: {bool(settings.LLM_API_KEY)}")

    if not settings.DEBUG:
        cors = settings.cors_origins_list
        if cors and all(("localhost" in origin or "127.0.0.1" in origin) for origin in cors):
            print("⚠️  CORS_ORIGINS appears localhost-only; hosted frontends will fail preflight (OPTIONS 400).")
    
    # Test database connectivity
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database connection error: {e}")

    # Optional: Log table count (dialect-agnostic)
    try:
        tables = inspect(engine).get_table_names()
        print(f"📚 Database tables: {len(tables)}")
    except Exception as e:
        print(f"⚠️  Table inspection failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown"""
    print(f"🛑 Shutting down {settings.APP_NAME}")
    try:
        llm_service = chat.get_llm_service()
        llm_service.close()
        print("✅ Closed LLM client")
    except Exception:
        pass


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint to verify system status.
    
    Returns:
        - status: Application health status
        - timestamp: Current server time
        - database_connected: Whether the configured database is accessible
        - llm_available: Whether the configured LLM appears configured
    """
    # Check database connection
    db_connected = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_connected = True
    except Exception as e:
        print(f"Health check - DB error: {e}")
    
    # Keep `/health` stable for hosting health checks: verify configuration only (no external API call).
    llm_available = bool(settings.LLM_API_KEY)
    
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
