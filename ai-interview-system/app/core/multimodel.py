import whisper
import torch
import logging

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
