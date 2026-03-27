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
#│   {"message": {"content": "面试者是一位约25岁的男性..."}} // 或者扫福瑞 笑:)
#│
#└─⑤ 返回

"""

其实，我们这里，应该先思考下原理的

一般地，我们可以把这里的步骤，分成五步：

第一步，构建消息列表：
    # 你传入的参数
prompt = "什么是多态？"
system_prompt = None

# chat() 方法内部做的事：拼一个列表
messages = []
# system_prompt 是 None，跳过
messages.append({"role": "user", "content": "什么是多态？"})

# 最终 messages 长这样：
[
    {"role": "user", "content": "什么是多态？"}
]

第二步：拼 HTTP 请求
# _call_deepseek() 内部做的事

# 拼请求体（JSON）
payload = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "user", "content": "什么是多态？"}
    ],
    "temperature": 0.7
}

# 拼请求头
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer sk-你的deepseek密钥"
}

第三步：发请求，拿响应：

你的电脑                                    DeepSeek 服务器
   │                                            │
   │  POST https://api.deepseek.com/chat/completions
   │  Headers: Authorization: Bearer sk-xxx
   │  Body: {"model":"deepseek-chat", "messages":[...]}
   │  ──────────────────────────────────────►   │
   │                                            │ DeepSeek 收到
   │                                            │ 开始推理...
   │                                            │ 生成回答...
   │                                            │
   │  HTTP 200 OK                               │
   │  Body: {"choices":[{"message":{"content":"多态是..."}}]}
   │  ◄──────────────────────────────────────   │
   │                                            │
   
第四步：解析响应，提取回答：
# DeepSeek 返回的原始 JSON 长这样：
{
    "id": "chatcmpl-xxx",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "多态是面向对象编程的核心特性之一..."  # ← AI的回答在这里
            }
        }
    ],
    "model": "deepseek-chat",
    "usage": {"prompt_tokens": 10, "completion_tokens": 50}
}

# 代码怎么取出来的：
content = data["choices"][0]["message"]["content"]
# → "多态是面向对象编程的核心特性之一..."

第五步：把结果封装成 LLMResponse 对象，返回给调用者：

# 把取出来的文本包成 LLMResponse 对象
return LLMResponse(
    content="多态是面向对象编程的核心特性之一...",
    model="deepseek-chat",
    provider="deepseek",
)

# 你拿到后：
resp.content  # → "多态是面向对象编程的核心特性之一..."
resp.model    # → "deepseek-chat"
resp.provider # → "deepseek"

"""



"""
llm_client.py
│
├── 数据结构
│   └── LLMResponse               ← 响应结果包装（没变）
│
├── 异常
│   ├── LLMClientError            ← 基类（没变）
│   ├── LLMConnectionError        ← 连不上（没变）
│   ├── LLMTimeoutError           ← 超时（没变）
│   └── LLMResponseError          ← 返回错误（没变）
│
├── LLMClient（核心类）
│   │
│   ├── 私有（内部自动调）
│   │   ├── _call_ollama()              ← 调本地 Ollama（识图用）
│   │   ├── _call_deepseek()            ← 调远程 DeepSeek（对话用）
│   │   └── _is_deepseek_available()    ← 检查 DeepSeek 网络是否通
│   │
│   └── 公开（你调这三个）
│       ├── chat()                 ← 纯文本对话 → 走 DeepSeek
│       ├── vision()               ← 纯图像识别 → 走本地 Ollama
│       ├── vision_from_file()     ← 传文件路径识图（自动转base64）
│       ├── vision_and_chat()      ← 图像+对话 → Ollama识图+DeepSeek对话（断网自动降级本地）
│       └── health_check()         ← 检查两个服务是否在线
│
└── llm_client                     ← 全局实例，import 直接用

"""


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


