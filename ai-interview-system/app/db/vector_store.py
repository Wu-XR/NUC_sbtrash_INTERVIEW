import os
from typing import Union
from app.config import settings

# 只有在安装了对应客户端时才导入，避免环境未安装时报错
try:
    import qdrant_client
    from langchain_qdrant import QdrantVectorStore
except ImportError:
    qdrant_client = None

try:
    from langchain_chroma import ChromaVectorStore
except ImportError:
    ChromaVectorStore = None


class VectorStoreManager:
    """
    向量数据库管理器
    根据环境变量选择具体的向量数据库实现
    """
    
    def __init__(self):
        self.client = self._init_client()
        self.store = self._init_store()

    def _init_client(self):
        """初始化底层数据库客户端"""
        provider = settings.VECTOR_DB_PROVIDER.lower()
        
        if provider == "qdrant":
            if not qdrant_client:
                raise ImportError("Qdrant client not installed. Run: pip install qdrant-client")
            return qdrant_client.QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
        elif provider == "chroma":
            if not ChromaVectorStore:
                raise ImportError("Chroma not installed. Run: pip install chromadb")
            # Chroma 通常直接在 VectorStore 中处理路径
            return None
        else:
            raise ValueError(f"Unsupported vector db provider: {provider}")

    def _init_store(self):
        """初始化 LangChain VectorStore"""
        provider = settings.VECTOR_DB_PROVIDER.lower()
        collection_name = settings.VECTOR_DB_COLLECTION
        
        if provider == "qdrant" and self.client:
            # 这里返回的是一个占位符，实际使用时需要传入 embedding function
            return QdrantVectorStore(
                client=self.client,
                collection_name=collection_name
            )
        elif provider == "chroma":
            return ChromaVectorStore(
                persist_directory=settings.CHROMA_PERSIST_DIR,
                collection_name=collection_name
            )

    def get_store(self):
        """获取向量存储实例（供 RAG 引擎调用）"""
        return self.store


# 创建全局单例
vector_store = VectorStoreManager()
