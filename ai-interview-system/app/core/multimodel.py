import whisper
import torch
import logging
import tempfile

# 相关信息请去看exp_multimodel.md快速上手

from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)

# 这个是选设备的函数，不传参数默认自动选择，传入参数可以强制使用某个设备
# 其实我觉得auto够用了，但是考虑到，万一某些电脑是N卡，想要快一点呢？

def _select_device(preferred: str = "auto") -> str:
    """自动选择推理设备"""
    if preferred == "auto":
        if torch.cuda.is_available():
            logger.info("CUDA available, using GPU")
            return "cuda"
        else:
            logger.info("CUDA not available, falling back to CPU")
            return "cpu"
    return preferred

# 这个其实没啥用就是，就是看你有没有CUDA，有CUDA用CUDA,然后，呃呃呃
# 然后记录到log

"""
    音频
      ↓
  multimodal.py（Whisper 转文字）
      ↓
  返回文本字符串
      ↓
  其他模块拿到文本去用（LLM 评分 / RAG 检索等）

"""


# ==================== 核心类 ====================

class AudioTranscriber:
    """
    Whisper 语音转文字工具

    用法：
        transcriber = AudioTranscriber()
        text = transcriber.to_text("interview.wav")
        # 拿到 text 传给其他模型就行了
    """

    def __init__(
            self,
            model_size: str = "small", # 模型大小
            device: str = "auto", # 设备选择，auto 会自动选 GPU（如果有）或 CPU
            language: str = "zh", # 语言设置，默认中文，提升识别准确率
    ):
        self.device = _select_device(device)
        self.language = language
        self.use_fp16 = (self.device == "cuda") # 有CUDA就用fp16
        logger.info(f"Loading Whisper [{model_size}] on [{self.device}]...")
        self.model = whisper.load_model(model_size, device=self.device)
        logger.info("Whisper model loaded.")

    # ---------- 核心方法：给其他模块调用的 ----------

    # 第一个方法会return一个相对简单的
    def to_text(
            self,
            audio_path: str,
            prompt: Optional[str] = None,
    ) -> str:
        """
        音频 → 纯文本（最常用，其他模块只需要这个）

        Args:
            audio_path: 音频文件路径
            prompt: 提示词，提升专业术语识别率

        Returns:
            转录出的文本字符串
        """
        result = self._transcribe(audio_path, prompt)
        return result["text"]
    # 第二个会返回更多的 detail
    def to_text_with_detail(
            self,
            audio_path: str,
            prompt: Optional[str] = None,
    ) -> dict:
        """
        音频 → 文本 + 详细信息（需要时间戳、置信度时用这个）

        Returns:
            {
                "text": "完整文本",
                "segments": [{"start": 0.0, "end": 3.5, "text": "..."}],
                "language": "zh"
            }
        """
        return self._transcribe(audio_path, prompt)

    def from_bytes(
            self,
            audio_bytes: bytes,
            suffix: str = ".wav",
            prompt: Optional[str] = None,
    ) -> str:
        """
        字节流 → 文本（FastAPI UploadFile 场景）

        用法：
            @router.post("/upload-audio")
            async def upload(file: UploadFile):
                text = transcriber.from_bytes(await file.read())
        """
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            return self.to_text(tmp.name, prompt)

    # ---------- 内部方法 ----------

    def _transcribe(self, audio_path: str, prompt: Optional[str] = None) -> dict:
        """内部转录逻辑"""
        logger.info(f"Transcribing: {audio_path}")

        result = self.model.transcribe(
            audio_path,
            language=self.language,
            fp16=self.use_fp16,
            initial_prompt=prompt or "这是一场技术面试。",
        )

        text = result["text"].strip()
        logger.info(f"Transcription done, length={len(text)} chars")

        return {
            "text": text,
            "segments": [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                }
                for seg in result.get("segments", [])
            ],
            "language": result.get("language", self.language),
        }


"""



"""