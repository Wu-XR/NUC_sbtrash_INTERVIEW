"""
Routers Package
"""

from .interview import router as interview_router
from .knowledge import router as knowledge_router
from .health import router as health_router

__all__ = ["interview_router", "knowledge_router", "health_router"]
