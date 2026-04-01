"""
app/core/__init__.py
面试系统核心模块的对外接口声明
作用：让外部模块能通过 'from app.core import xxx' 直接导入我们需要的工具
"""

# 从 multimodal.py 导出语音转文字工具
from .multimodel import AudioTranscriber

# 从 llm_client.py 导出大模型客户端和相关枚举
from .llm_client import llm_client, LLMProvider, LLMResponse

# __all__ 定义了当使用 'from app.core import *' 时，具体导入哪些核心类
# 这是一种保护机制，防止把内部的辅助函数（如异常类、私有方法）也导出去
__all__ = [
    "AudioTranscriber",  # 语音识别器
    "llm_client",       # 预先配置好的 LLM 客户端实例（单例）
    "LLMProvider",      # 枚举：说明是用了本地 Ollama 还是远程 DeepSeek
    "LLMResponse",      # 类：封装了模型返回的内容
]
