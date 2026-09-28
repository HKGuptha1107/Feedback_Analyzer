"""Main FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, SessionLocal
from app.api.routes_feedback import router as feedback_router
from app.api.routes_memory import router as memory_router
from app.services.feedback_service import ensure_default_product


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle handler."""
    init_db()
    
    db = SessionLocal()
    try:
        ensure_default_product(db, product_id="flowdesk", name="Feedback Analyzer")
    finally:
        db.close()
    
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous Product Feedback Intelligence Agent powered by Groq LLM & Hindsight Persistent Agent Memory.",
    lifespan=lifespan,
)

# CORS configuration
origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(feedback_router)
app.include_router(memory_router)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint to verify backend operational readiness."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "connected",
        "hindsight_bank": settings.HINDSIGHT_BANK_ID,
    }


@app.get("/", tags=["Root"])
def root():
    """Root welcoming endpoint pointing to Swagger docs."""
    return {
        "message": "Welcome to Feedback Analyzer API",
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.BACKEND_PORT, reload=True)
