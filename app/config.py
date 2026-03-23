from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    APP_NAME: str = "AI面试系统"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "RAG容器运行的AI面试系统"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    REDIS_URL: str = "redis://localhost:6379"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    
    DEFAULT_LLM_MODEL: str = "Qwen3"
    EMBEDDING_MODEL: str = "Qwen3-Embedding-0.6B"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
