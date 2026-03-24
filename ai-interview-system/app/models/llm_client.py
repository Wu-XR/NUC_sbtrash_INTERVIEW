"""
LLM 调用封装 —— 通过 HTTP 调用本地 Ollama 服务
"""
import base64
import httpx
from pathlib import Path
from typing import Optional
from openai import OpenAI
import json
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator, Union
from enum import Enum
# from app.config import settings

# 日志配置
logger = logging.getLogger(__name__)


# 这一部分，是调用本地 Ollama ，我们要用到qwen2.5 -vl 7b来处理图像

#├─① cv2.VideoCapture(0)     → 打开摄像头拍照，保存为 .jpg
#│
#├─② base64.b64encode(图片)   → 把图片变成文字字符串
#│
#├─③ HTTP POST 到 Ollama      → 发送到 localhost:11434/api/chat
#│   {                             ┌─────────────────────┐
#│     "model": "qwen2.5-vl:7b",   │  Ollama 收到请求     │
#│     "messages": [{              │  ↓                  │
#│       "content": "请描述...",    │  qwen2.5-vl 模型推理 │
#│       "images": ["base64..."]   │  （GPU 在这里干活）   │
#│     }]                          │  ↓                  │
#│   }                             │  返回文字结果         │
#│                                 └─────────────────────┘
#├─④ 收到 JSON 响应
#│   {"message": {"content": "面试者是一位约25岁的男性..."}}
#│
#└─⑤ 返回


# ============================================================================
# 常量与枚举
# ============================================================================

class LLMProvider(str, Enum):
    """LLM 提供商枚举"""
    OLLAMA = "ollama"       # 本地 Ollama
    OPENAI = "openai"       # OpenAI API


# Ollama API 默认地址
OLLAMA_BASE_URL = "http://localhost:11434"

# OpenAI API 地址
OPENAI_BASE_URL = "https://api.deepseek.com"
# 其实这里，呃，本地模型一般比较慢，实时问答这些东西，我建议用deepseek、
# 支持国货，我是吴京的，所以用deepseek

# 默认超时时间（秒）—— 本地 7B 模型推理可能较慢，给足时间
DEFAULT_TIMEOUT = 300.0

# 默认重试次数 —— 本地服务偶尔可能请求失败，适当重试
DEFAULT_MAX_RETRIES = 3


class ChatMessage:
    """统一消息结构，一份数据两种输出"""

    def __init__(self, role: str, content: str, images: Optional[List[str]] = None):
        self.role = role  # "system" / "user" / "assistant"
        self.content = content  # 文本内容
        self.images = images or []  # 图片（base64），多模态用

    def to_ollama_dict(self) -> Dict[str, Any]:
        """转成 Ollama 要的格式"""
        msg = {"role": self.role, "content": self.content}
        if self.images:
            msg["images"] = self.images  # Ollama 就是直接放 images 字段
        return msg

    def to_openai_dict(self) -> Dict[str, Any]:
        """转成 OpenAI 要的格式"""
        if self.images:
            # OpenAI 要把文本和图片拆成 content 数组
            content_parts = [{"type": "text", "text": self.content}]
            for img in self.images:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img}"}
                })
            return {"role": self.role, "content": content_parts}
        return {"role": self.role, "content": self.content}
