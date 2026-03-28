import time
import whisper
import torch
import logging
import tempfile
import os
import cv2
from .llm_client import LLMClient

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

# ====================================================================================================
# 关于视频处理的部分
# ====================================================================================================

"""

我的一点想法

其实由于前面我们已经写好了给模型传图片的接口，所以我们这里其实要干的就是

调用摄像头
    |
获取视频帧
    |
拍照
    |
存储下来
    |
发给本地部署的Ollama小模型 qwen2.5vl:7b 让这个模型来分析照片里的内容，给出一些分析结果（比如表情、姿态、眼神等等），用于面试参考
接着，生成json，进一步处理

我接口前面倒是写好了，现在我们要完成这些相关的函数

"""

# 拍照的默认存储目录，运行时如果不存在会自动创建
CAPTURE_DIR = "uploads/captures"


class VideoCapture:
    """摄像头操作工具：打开摄像头 → 拍照 → 存成 jpg → 返回文件路径"""

    def __init__(self, camera_id: int = 0, save_dir: str = CAPTURE_DIR):
        # camera_id: 摄像头编号，0 是电脑默认摄像头，1 是第二个，以此类推
        self.camera_id = camera_id
        # save_dir: 照片存到哪个文件夹，默认用上面定义的 CAPTURE_DIR
        self.save_dir = save_dir
        # 如果文件夹不存在就创建，exist_ok=True 表示已存在也不报错
        os.makedirs(self.save_dir, exist_ok=True)

    def capture_frame(self, filename: Optional[str] = None) -> str:
        """拍一张照片，返回保存路径"""

        # 打开摄像头，得到一个摄像头对象 cap
        cap = cv2.VideoCapture(self.camera_id)

        # 检查摄像头是否成功打开（没摄像头、被占用等情况会失败）
        if not cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 {self.camera_id}")

        # 从摄像头读取一帧画面
        # ret: bool，True 表示读取成功，False 表示失败
        # frame: numpy 数组，就是这一帧的图像像素数据，shape 类似 (480, 640, 3)
        ret, frame = cap.read()

        # 释放摄像头，不释放的话其他程序就打不开它了
        cap.release()

        # 如果读取失败或者拿到的是空数据，报错
        if not ret or frame is None:
            raise RuntimeError("摄像头读取帧失败")

        # 如果调用时没传文件名，就用当前时间戳自动生成一个
        # 比如 "1711612800.jpg"
        if filename is None:
            filename = f"{int(time.time())}.jpg"

        # 拼出完整的保存路径，比如 "uploads/captures/1711612800.jpg"
        save_path = os.path.join(self.save_dir, filename)

        # 用 OpenCV 把 frame（numpy 数组）写成 jpg 图片文件存到磁盘
        cv2.imwrite(save_path, frame)

        # 打日志记录一下存到了哪里
        logger.info(f"Captured frame saved: {save_path}")

        # 返回文件路径字符串，后续可以丢给调用
        return save_path