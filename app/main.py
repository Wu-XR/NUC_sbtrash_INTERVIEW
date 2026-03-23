from fastapi import FastAPI
from app.routers import interview, knowledge, health

app = FastAPI(
    title="AI Interview System",
    description="An AI-powered interview system with RAG capabilities",
    version="1.0.0"
)

app.include_router(
    interview.router,
    prefix="/api/v1/interview",
    tags=["interview"]
)

app.include_router(
    knowledge.router,
    prefix="/api/v1/knowledge",
    tags=["knowledge"]
)

app.include_router(
    health.router,
    prefix="/api/v1/health",
    tags=["health"]
)

@app.get("/")
async def root():
    return {"message": "AI Interview System API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# app/__init__.py
"""
AI Interview System Package
"""

from .main import app

__all__ = ["app"]
