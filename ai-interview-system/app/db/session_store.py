import redis
import json
from typing import Dict, Any, Optional
from app.config import settings


class InterviewSessionStore:
    """
    面试会话存储
    用于在多轮面试中保持用户状态
    Key: interview:{user_id}:{session_id}
    """
    
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True  # 确保字符串自动解码
        )
        # 会话过期时间（秒），例如 2 小时
        self.ttl = settings.SESSION_TTL_SECONDS

    def save_session(self, user_id: str, session_id: str, data: Dict[str, Any]) -> bool:
        """
        保存会话数据
        """
        key = f"interview:{user_id}:{session_id}"
        try:
            # 使用 JSON 序列化复杂对象
            self.client.setex(
                key, 
                self.ttl, 
                json.dumps(data, ensure_ascii=False)
            )
            return True
        except redis.RedisError as e:
            print(f"Redis save error: {e}")
            return False

    def load_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        加载会话数据
        """
        key = f"interview:{user_id}:{session_id}"
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except redis.RedisError as e:
            print(f"Redis load error: {e}")
            return None

    def delete_session(self, user_id: str, session_id: str) -> bool:
        """
        删除会话（面试结束时调用）
        """
        key = f"interview:{user_id}:{session_id}"
        try:
            self.client.delete(key)
            return True
        except redis.RedisError as e:
            print(f"Redis delete error: {e}")
            return False


# 创建全局单例
session_store = InterviewSessionStore()
