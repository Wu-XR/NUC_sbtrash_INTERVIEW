"""
LLM 调用封装 —— 通过 HTTP 调用本地 Ollama 服务
"""
import base64
import httpx
import logging
from typing import Optional, List, Dict, Any
from enum import Enum
from ..config import settings  # 相对导入项目配置（包含 env 变量）

# 日志配置
logger = logging.getLogger(__name__)


# 这一部分，是调用本地 Ollama ，我们要用到qwen2.5 -vl 7b来处理图像

#├─① cv2.VideoCapture(0)     → 打开摄像头拍照，保存为 .jpg
#│
#├─② base64.b64encode(图片)   → 把图片变成文字字符串
#│
#├─③ HTTP POST 到 Ollama      → 发送到 localhost:11434/api/chat
#│   {                             ┌─────────────────────┐
#│     "model": "qwen2.5vl:7b",   │  Ollama 收到请求     │
#│     "messages": [{              │  ↓                  │
#│       "content": "请描述...",    │ qwen2.5vl:7b模型推理 │
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
│   └── LLMProvider               ← 提供包装
│   └── LLMResponse               ← 响应结果包装
│
├── 异常
│   └── LLMClientError（我们定义的，LLM 异常的老大）
│       ├── LLMConnectionError（连不上）
│       ├── LLMTimeoutError（超时）
│       └── LLMResponseError（返回错误）
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
    """LLM 提供商"""
    OLLAMA = "ollama"         # 本地 Ollama — 图像识别
    DEEPSEEK = "deepseek"     # 远程 DeepSeek — 文本对话


# 默认地址
OLLAMA_BASE_URL = "http://localhost:11434"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 默认超时（秒）— 本地 7B 模型推理慢，给足时间
DEFAULT_TIMEOUT = 300.0

# 默认重试次数
DEFAULT_MAX_RETRIES = 3


# ============================================================================
# 响应结构
# ============================================================================

class LLMResponse:
    """
    LLM 响应结果

    Attributes:
        content:  AI 回复的文本（最常用，拿这个就行）
        model:    用了哪个模型（"qwen2.5vl:7b" 或 "deepseek-chat"）
        provider: 谁提供的（LLMProvider.OLLAMA 或 LLMProvider.DEEPSEEK）
    """
    def __init__(
        self,
        content: str,
        model: str = "",
        provider: LLMProvider = LLMProvider.OLLAMA,
    ):
        self.content = content
        self.model = model
        self.provider = provider

    def __str__(self) -> str:
        return self.content

    def __repr__(self) -> str:
        return f"LLMResponse(provider='{self.provider.value}', model='{self.model}')"

# ============================================================================
# 异常类
# =============================================================================

"""
├── LLMClientError            ← 基类（没变）
├── LLMConnectionError        ← 连不上（没变）
├── LLMTimeoutError           ← 超时（没变）
└── LLMResponseError          ← 返回错误（没变）
"""

# 第一层：基类，所有 LLM 错误的"老大"
class LLMClientError(Exception):
    def __init__(self, message="LLM 服务异常", detail=""):
        self.message = message    # 错误信息（简短）
        self.detail = detail      # 详细原因（排查用）
        super().__init__(self.message)  # 告诉 Python 的 Exception 基类

# 第二层：具体的错误类型，都继承自"老大"
class LLMConnectionError(LLMClientError):    # 连不上
    def __init__(self, message="无法连接到 LLM 服务", detail=""):
        super().__init__(message, detail)

class LLMTimeoutError(LLMClientError):       # 超时
    def __init__(self, message="LLM 请求超时", detail=""):
        super().__init__(message, detail)

class LLMResponseError(LLMClientError):      # 返回的数据有问题
    def __init__(self, message="LLM 响应异常", detail=""):
        super().__init__(message, detail)

# ============================================================================
# 这里定义LLMClient（核心类）
# ===========================================================================

# ============================================================================
# 核心类：LLMClient
#
# 只有三个公开方法，对应你的三个需求：
#   1. chat()             → 纯文本对话（走 DeepSeek）
#   2. vision()           → 纯图像识别（走本地 Ollama）
#   3. vision_and_chat()  → 图像+对话（Ollama识图 + DeepSeek对话，断网时本地兜底）
# ============================================================================

class LLMClient:

    def __init__(
        self,
        # Ollama（本地图像识别）
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "qwen2.5vl:7b",
        # DeepSeek（远程对话）
        deepseek_base_url: str = "https://api.deepseek.com",
        deepseek_model: str = "deepseek-chat",
        deepseek_api_key: Optional[str] = None,
        # 通用参数
        timeout: float = 300.0,
        max_retries: int = 3,
    ):
        # 本地 Ollama 配置
        self.ollama_base_url = ollama_base_url  # Ollama 服务地址（本地）
        self.ollama_model = ollama_model        # Ollama 要使用的模型名

        # 远程 DeepSeek 配置
        self.deepseek_base_url = deepseek_base_url  # DeepSeek API 基础地址
        self.deepseek_model = deepseek_model        # DeepSeek 要使用的模型名
        # DeepSeek 的 API key（优先参数传入，否则从 settings 中读取）
        # 使用 getattr 以防 settings 中未定义 DEEPSEEK_API_KEY，避免属性错误
        self.deepseek_api_key = deepseek_api_key or getattr(settings, "DEEPSEEK_API_KEY", None)

        # 通用超时与重试设置
        self.timeout = timeout            # 单次请求超时时间（秒）
        self.max_retries = max_retries    # 遇到网络或超时错误时的重试次数

        # 记录初始化信息，便于运行时查看当前配置
        logger.info(
            f"LLMClient 初始化 | 图像识别={self.ollama_model}@{self.ollama_base_url} | "
            f"对话={self.deepseek_model}@{self.deepseek_base_url}"
        )

    # ----------------------------------------------------------------
    # 内部：调用本地 Ollama
    # ----------------------------------------------------------------

    async def _call_ollama(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
    ) -> LLMResponse:

        # 构造 Ollama 要求的请求体（包括 model、messages、options）
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        # 按重试次数尝试请求 Ollama
        for attempt in range(1, self.max_retries + 1):
            try:
                # 使用 httpx.AsyncClient 发送 POST 请求到 /api/chat
                async with httpx.AsyncClient(
                    base_url=self.ollama_base_url,
                    timeout=httpx.Timeout(self.timeout),
                ) as client:
                    resp = await client.post("/api/chat", json=payload)
                    resp.raise_for_status()  # 抛出 HTTP 错误以便统一处理
                    data = resp.json()

                # 从响应中提取模型返回的文本（message.content）并封装返回
                return LLMResponse(
                    content=data.get("message", {}).get("content", ""),
                    model=self.ollama_model,
                    provider=LLMProvider.OLLAMA,
                )

            except httpx.ConnectError as e:
                # 连接失败：记录并在最后一次尝试失败时抛出专用异常
                logger.error(f"Ollama 连接失败（第{attempt}次）: {e}")
                if attempt == self.max_retries:
                    raise LLMConnectionError(
                        message="无法连接到 Ollama",
                        detail=f"请确认已启动：ollama serve，地址：{self.ollama_base_url}",
                    ) from e

            except httpx.TimeoutException as e:
                # 请求超时：记录并在最后一次尝试失败时抛出专用异常
                logger.error(f"Ollama 超时（第{attempt}次）: {e}")
                if attempt == self.max_retries:
                    raise LLMTimeoutError(
                        message=f"Ollama 请求超时（{self.timeout}秒）",
                        detail="本地7B模型推理较慢，可尝试增大timeout",
                    ) from e

            except httpx.HTTPStatusError as e:
                # 非 2xx 响应，封装为 LLMResponseError 抛出
                raise LLMResponseError(
                    message=f"Ollama 返回错误: {e.response.status_code}",
                    detail=e.response.text,
                ) from e

    # ----------------------------------------------------------------
    # 内部：调用远程 DeepSeek
    # ----------------------------------------------------------------

    async def _call_deepseek(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
    ) -> LLMResponse:

        # 构造与 OpenAI 兼容的请求体
        payload = {
            "model": self.deepseek_model,
            "messages": messages,
            "temperature": temperature,
        }

        # 请求头需要 Authorization（Bearer token）
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}",
        }

        # 按重试次数尝试请求 DeepSeek
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    base_url=self.deepseek_base_url,
                    headers=headers,
                    timeout=httpx.Timeout(self.timeout),
                ) as client:
                    resp = await client.post("/chat/completions", json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                # 按 OpenAI 返回结构解析出文本回答
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                return LLMResponse(
                    content=content,
                    model=self.deepseek_model,
                    provider=LLMProvider.DEEPSEEK,
                )

            except httpx.ConnectError as e:
                # 网络连接问题 -> 在最后一次失败时抛出 LLMConnectionError
                logger.error(f"DeepSeek 连接失败（第{attempt}次）: {e}")
                if attempt == self.max_retries:
                    raise LLMConnectionError(
                        message="无法连接到 DeepSeek API",
                        detail=f"地址：{self.deepseek_base_url}，请检查网络",
                    ) from e

            except httpx.TimeoutException as e:
                # 请求超时 -> 抛出超时错误
                logger.error(f"DeepSeek 超时（第{attempt}次）: {e}")
                if attempt == self.max_retries:
                    raise LLMTimeoutError(
                        message="DeepSeek 请求超时",
                    ) from e

            except httpx.HTTPStatusError as e:
                # 非 2xx 响应 -> 抛出响应错误
                raise LLMResponseError(
                    message=f"DeepSeek 返回错误: {e.response.status_code}",
                    detail=e.response.text,
                ) from e

    # ----------------------------------------------------------------
    # 内部：检查 DeepSeek 是否可用（网络是否通）
    # ----------------------------------------------------------------

    async def _is_deepseek_available(self) -> bool:
        # 用短超时请求 DeepSeek /models 接口，成功则认为可用
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                resp = await client.get(f"{self.deepseek_base_url}/models", headers={
                    "Authorization": f"Bearer {self.deepseek_api_key}",
                })
                return resp.status_code == 200
        except Exception:
            # 任意异常都视为不可用（网络或认证问题）
            return False

    # ================================================================
    # 公开接口 1：chat() — 纯文本对话
    #
    # 原理：
    #   把你说的话包成 messages 数组 → 发给 DeepSeek → 拿回回答
    #
    #   messages 长这样：
    #   [
    #     {"role": "system", "content": "你是面试官"},   ← 可选
    #     {"role": "user", "content": "什么是多态？"}     ← 你的问题
    #   ]
    # ================================================================

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        纯文本对话 → 走 DeepSeek API

        Args:
            prompt:        你要问的话
            system_prompt: 系统提示词（告诉AI它是谁）
            temperature:   温度，越高越随机（0~1）

        Returns:
            LLMResponse，用 resp.content 拿回答文本

        Example:
            resp = await llm_client.chat("什么是多态？")
            print(resp.content)
        """
        messages = []
        # 如果传入系统提示，先加入 system 消 Messages
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        # 用户消息放在 messages 列表末尾
        messages.append({"role": "user", "content": prompt})

        # 发给 DeepSeek 并返回 LLMResponse
        return await self._call_deepseek(messages, temperature=temperature)

    # ================================================================
    # 公开接口 2：vision() — 纯图像识别
    #
    # 原理：
    #   图片转成 base64 字符串 → 塞进 messages 的 images 字段
    #   → 发给本地 Ollama → qwen2.5-vl 看图 → 返回描述文本
    #
    #   发给 Ollama 的 JSON 长这样：
    #   {
    #     "model": "qwen2.5vl:7b",
    #     "messages": [{
    #       "role": "user",
    #       "content": "描述这张图片",
    #       "images": ["base64字符串..."]    ← 图片在这里
    #     }]
    #   }
    # ================================================================

    async def vision(
        self,
        images: List[str],
        prompt: str = "请详细描述这张图片的内容",
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """
        纯图像识别 → 走本地 Ollama（qwen2.5vl:7b）

        Args:
            images:        base64 编码的图片列表
            prompt:        让模型做什么（默认"描述图片内容"）
            system_prompt: 系统提示词
            temperature:   图像识别建议低温度（0.3），结果更稳定

        Returns:
            LLMResponse，resp.content 是图片的描述文本

        Example:
            import base64
            with open("photo.jpg", "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            resp = await llm_client.vision([img_b64])
            print(resp.content)  # "图片中是一个人坐在桌前..."
        """
        messages = []
        # 可选的 system 提示
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        # 将 base64 图片列表放进 images 字段，作为 user 消息的一部分
        messages.append({
            "role": "user",
            "content": prompt,
            "images": images,
        })

        # 发给本地 Ollama 识别并返回 LLMResponse
        return await self._call_ollama(messages, temperature=temperature)

    # ================================================================
    # 公开接口 2.5：vision_from_file() — 传文件路径的便捷方法
    #
    # 原理：
    #   读文件 → 转 base64 → 调 vision()
    #   就是帮你省了手动转 base64 的步骤
    # ================================================================

    async def vision_from_file(
        self,
        image_path: str,
        prompt: str = "请详细描述这张图片的内容",
        **kwargs,
    ) -> LLMResponse:
        """
        传文件路径的图像识别（自动转 base64）

        Example:
            resp = await llm_client.vision_from_file("/tmp/photo.jpg")
        """
        # 读取文件并转为 base64 编码字符串
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        # 复用 vision 接口进行识别
        return await self.vision([img_b64], prompt=prompt, **kwargs)

    # ================================================================
    # 公开接口 3：vision_and_chat() — 图像 + 对话
    #
    # 原理（两步走）：
    #
    #   第一步：把图片发给本地 Ollama → 拿到图片描述
    #   第二步：把"图片描述 + 你的问题"一起发给 DeepSeek → 拿到最终回答
    #
    #   流程图：
    #   图片 → Ollama(本地) → "图中是一个人在写代码"
    #                              ↓
    #   "图中是一个人在写代码" + "他的代码有什么问题？" → DeepSeek(远程) → 最终回答
    #
    #   如果 DeepSeek 连不上（断网）：
    #   图片 + 你的问题 → 全部给 Ollama(本地) → 本地兜底回答
    # ================================================================

    async def vision_and_chat(
        self,
        images: List[str],
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        图像 + 对话 → 先 Ollama 识图，再 DeepSeek 对话
        网络不好时自动降级为全部本地处理

        Args:
            images:        base64 图片列表
            prompt:        你的问题
            system_prompt: 系统提示词
            temperature:   温度

        Returns:
            LLMResponse

        Example:
            resp = await llm_client.vision_and_chat(
                images=[img_b64],
                prompt="这个人的表情说明了什么？",
                system_prompt="你是面试分析专家"
            )
        """
        # 第一步：本地识图
        logger.info("vision_and_chat | 第一步：本地识图...")
        vision_result = await self.vision(
            images=images,
            prompt="请详细描述这张图片中的所有内容",
            temperature=0.3,
        )
        image_description = vision_result.content  # 从 LLMResponse 中拿到文本
        logger.info(f"vision_and_chat | 识图结果：{image_description[:100]}...")

        # 第二步：尝试用 DeepSeek 对话
        if await self._is_deepseek_available():
            logger.info("vision_and_chat | 第二步：DeepSeek 对话")
            # 把图片描述拼入 prompt 中，发给 DeepSeek
            combined_prompt = (
                f"以下是一张图片的内容描述：\n"
                f"---\n{image_description}\n---\n\n"
                f"基于以上图片内容，请回答：{prompt}"
            )
            return await self.chat(
                prompt=combined_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
            )

        # DeepSeek 不可用 → 降级为本地全部处理（把图片和问题一起发给 Ollama）
        else:
            logger.warning("vision_and_chat | DeepSeek 不可用，降级为本地处理")
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({
                "role": "user",
                "content": prompt,
                "images": images,
            })
            return await self._call_ollama(messages, temperature=temperature)

    # ================================================================
    # 健康检查
    # ================================================================

    async def health_check(self) -> Dict[str, bool]:
        """
        检查两个服务是否都在线

        Returns:
            {"ollama": True/False, "deepseek": True/False}
        """
        ollama_ok = False
        deepseek_ok = False

        # 检查本地 Ollama 的 /api/tags 接口是否可达
        try:
            async with httpx.AsyncClient(
                base_url=self.ollama_base_url,
                timeout=httpx.Timeout(5.0),
            ) as client:
                resp = await client.get("/api/tags")
                ollama_ok = resp.status_code == 200
        except Exception:
            # 任意异常都认为 Ollama 不可用
            pass

        # 检查 DeepSeek 可用性
        deepseek_ok = await self._is_deepseek_available()

        return {"ollama": ollama_ok, "deepseek": deepseek_ok}


# ============================================================================
# 全局实例：直接 import 使用
# ============================================================================

# 创建一个模块级的 LLMClient 实例，方便其他模块直接 import 使用
llm_client = LLMClient()

"""
-==+*=-=====+++=-==+++*#*+=-=-+@*-=-=+*###*##%%%##**+++===--------=======++=++-=====-+%#=-==+**=--==
+%#%%+-==-+#%%%=-+++++=----==-=#+-=+*++**#################****++===-----=%%=+*-==----+**==+--=+##=--
=*#%#=+=-===#**=-=----+*####*+-----+*####%*+==+++++++++++++******##***+===----=*###*+=---==--=-=*%*=
--===-=++====--======%%*+=====--=*#%#%#++#+=+=++++++==+++++%%##*##*##*##***++==--=+#%@%*=-*#+--=-+%%
===-=**===----=====-*@=---=---+#%%%*+++=====+=++++++==++=++#@#%#%@%%%%%#*###**#**+=--=*%@%++%#=-=-=#
====#*--===#%+-==---*@+-=--=*%@%**#+===++=====+++++++++++++%@%#%#%%#%@%%%%@#==+=+**#*+===#%=-#@+-=--
==-+%-===-=*%+=--=*%%#=--=#@@**%*+=====+======+++++++++++++%@@%##%%#%@%##%@#+======+*****=-==-++-===
==-+%=====-----=#%#+=--=#@%##*#*===+===+=======+++++*%#*++*%%@@@@@%%@%#%%%@*=========++=*@=--=--====
=-=*#==-+%##*-=@%+*=-=#@@*=+#%+========++=======+++++*++*+++++**###%%###%%%+==+++=====+*+%#=======--
-+#+==-=%@@@%==+-=#**%@#+=+##*+*****++=++========++++==+*+===========++++++==++**===****++%#*=----==
#%=-=====*@*+=--*#%%%%%%@@%%#%%@@@@@@%%##*+=======+++++===============+=====+%%+===*#**+==#%--+*+*%%
%=-====--=+=+=+%##@@@@@@@@@@@@@@@@@@@@@@@@@%*=======+++===========+#*=+=====++*+==========+@*-+%%%%%
=--==--+=-=%+*%*%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#++***#####**++++===+#*===+==================#@=++##*=
-++--=#*-=@+=%*%@@@@@@@@@@@@@%%%%#@@@@@@@@@@@@@@#%@@@@@@@@@@%%#++========+==================@*+--=--
-==-=%*--+%-*##@@@@@@@@%#%%%%%@%#%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@%%**======++==++**=======++++%%+*====
##=-#%-====+%*#@@@@@@@@@#%%@@@%%#%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@%+=====+++=#%%%#====*%#*+++%##+---
%%+=@*-==-*@*#%@@@@@@@%%%@@@@@@%@%%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#++====*++%#**====+++====%#-+#+=
==-=@*-=-=@%*@@@@@@@@%%%%%%%%@%#%%%%@@@@@@@%%%%%@@@@@@@@@@@@@@@@@@@@@%%%#*+*#+===============*@+@@@#
==-=@%--+@%##@@@@@@@@@@%%%%#%%#@@@@@@@@@@%%%@@%%%%@@@@@@@@@@@@@@@@@@@@@@@@%###+============++=@**##*
===-*@*=@%@%*%@@@@@@@@@@@@@%%%@@@@@%@@@@%%%#%@%#@%@@@@@@@@@@@@@@@@@@@@@@@@@@@%#*==+#*======**=#@-=--
==-==**#@%@@%#%%@%%%@@@@@@%@@@@@@#%%%%@@@%%%%%%%%%@@@@@@@@@@@@@@@@@@@@@@@@@@@@%#*=+*++========%@=%==
-=-=*--@%#@%@@%%%%%%@%%%%%%%@@@@@%%%%@@@@@%%%%%%@@@@@@%#%%@@@@@@@@@@@@@@@@@@@@@%*#+========*++@%%#-=
+=-+%#=%@#@@@@@@@@@@@@@@@@@@@%@@@@@@@@@@@@@@@@@@@%%@@@%#%#@@@@@@@@@@@@@@@@@@@@@@%*#+==+====+=#@%*=--
##+*#%#%@#+%@%%@@@@@@@@@@@@@@@@@%%@@@@@@@@@@@%%@@%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#=+=*%+==+*+%%@*-*+
%%%%%%%%%%#+#@@@@@@@@@@@@@@@@@@@@@@@%%%%%%%%%%%%@@@%%%@@@@@@@@@@@@@@@@@@@@@@@@@@@*+===+====+%@%@@-*%
@@@@@@@@@@%#@@@@@@@@@@@%%%@@@%#*#@@@@@@@@@@@@@@@@%@%%@@@@@@@@@@@@@@@@@@@@@@@@@@@@*+======+*%@@@%@==%
@@@@@@@@@#%@@@@@@@@@%#%@@@@%##%%*@@@@@@@@@@@@@@@%%%@@@@@@@@@@@@@@@%@@@@@@@@@@@@@%*=======*@@@@%%@=+%
@@@@@@@@#@@@@@@@@@@@%*=*****#%%%*@@@@@@@@@@@@@@@@@@%#%%@@@@@@%%%%%%%@@@@@@@@@@@@#+=====+#%@@@@#@%-=#
@@@@@@%#%@@@@@@@@@@##%*==*====+#*%@@@@@@@@@@@@@@@@@#%@@@@%#@%%#%@@@@%%@%%@@@@%@@#+====+#@@@@%#%@#=-=
@@%@%%%%@@@@@@@@@@@*@@@%+==++===+*@@@@@@@@@@@@@@@@%#@@@@@#%@%@*%@%%%%@%%%%%%%##%*=====%@%%%##@##@+-=
@@%%@@@@@@@@@@@@@@%#@@@@####%%%#*+#@@@@@@@@@@@@@@%%%#%%##+#%#@%*@@@%%#%%@@@@%%%#*===+%@%%#%*@*+@@=-=
@@@%##%@@@@@@@@@@@@#@@@%#@@@@@@@@@*%@@@@@@@@@@@%#*++==--==-==++++%@@@@%%@@@@@@@#+==+%%%%%%##@*@@*--=
@@@@%+@@@@@@@@@@@@@%%@@#@@@@@@@@@@@*#@@@@@@@@%#++**##**++===--===+*%@@@@@%##**##+=*##**#%##@%=#@%===
###%#+@@@@@@@@@@@@@@%%%#@@@%#@@@@%##**%@@@@@@%*%@@@@@@@%#****+=-=*==+*##*=----+%+#@@@@#**#@%=--*#+%+
@@#%%**@@@@@@@@@@@@@@@%%@%@%%@@%%##****#@@@@@@%#@@@@@@@@@%#*+**=-===+*+---====*##@@@@@@@@%%#+**+====
@@@#%@*#@@@@@@@@@@@@@@@@@@%%@@@%*****#%%*%@@@@@@%%@@@@@@@@@%--++%%%%@%==#%@@@@@%%@@@@@@@@@@@@%#+====
@@@%%@@##@@@@@@@@@@@@@@@%#%@@@@@%+#%%%@%#%%%%%%@@%%%@@@@@@@%-=-+%@@@*-=%@@@@@@@@@%@@@@@@#+#%*--==-==
@@%@@@@@**%%%@@@@@@@%%##%@%@@@@@@@@@@@@%@@@@@@@#%@@@@@@@@@@+-==%#%%=-=#@@@@@@@@@@%@@@@@@@**%@%=*@+--
@@%%%###%@@%#######**#*%@@@%@@@@@@@@@@@@@@@@@@@##@@@@@@%%%*-=-=@@+-===#@@@@@@@@@%%@@@@@@@#*%##@#%@%*
@%**#%%#%@@@@@@@@@@*#@%%%@@@@%@%%%%@@@@@@@@@@@@#+#%%%%@@@@===-*#=====--#@@@@@@@%%@@@@@@@@%+@@%#%%%#%
*+++++#+@@@@@@@@@@@*%%%%%%%@@%@@%@@%@%%%@@@@%%*+*%@@@@@@@*==+=**-====*+==+*##++#@@@@@@@@@%*@@@@%##%*
=++++***@@@@@@@@@@@%#@%%%%%#%%@@@@@@@@@@@@%%%*#%@@@@@@@%==++=-*@*==-#%+-=----=%@@@@@@@@@@%*@@@@@@%#%
+++++++*@@@@@@@@@@@@#%%%%%%@@*#%@%%%%%@@%%@%+#@@@@@@@@*=+++==+#@@%*++=-===+*%@@@@@@@@@@@@##@@@@@@@@@
++++++++%@@@@@@@@@@@@%#%%@@@%%@@%@@@@#@@@@@##@@@@@@@#==++++=+++%@@@@@%%%%@@@@@@@@@@@@@@@@#@@@@@@@@@@
=++++++++%@@@@@@@@@@@@@@@%%%@#@@@@@@##@@@@@*%@@@@@@%=+****+++++*@@@@@@@@@@@@@@@@@@@@%@@@%@@@@@@@@@@@
=+++++++++#%%@@@@@@@@@@%%%@@@#@@@@%*#%%##**+%@@@@@@#**++++****++#@@@@@@@@@@@@@@@@@@##@@%%@@@@@@@@@@@
==++*%*++*@@%%%%%%%%#%%%@@@%%%%@@@@%%%*++**+*@@@@@@@%%##%%%*****+*%@@@@@@@@@@@@@@%*+@@%@@%%@@@@@@@@@
===++#+++*****@@@@@@*@@@@@@@*%%@@@@@@++*+***+*%@@@@@@@@@%#***+**++#@@@%@@@@@@@@%#*+%%*#%%%#%@@@@@@@%
=====+++++++++#@@@@@%*@@@@@@#+#%@@@@%=********+*##%###********+++*@%##*%#%%%%%##%%%%%@@%#%%%@@@@@@@@
======+++++++++***%@@%#@@@@@@*%%@@@@@=+++********++++******+++*#@%@#%@#@%###%@%%@%+-=++#%%*%%%%%##**

"""