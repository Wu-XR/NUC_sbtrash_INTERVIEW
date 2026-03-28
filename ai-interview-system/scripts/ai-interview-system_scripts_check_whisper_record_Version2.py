#!/usr/bin/env python3
"""
测试脚本：临��文件夹 → 录音 → Whisper 语音转文字 → 删除临时文件夹

流程：
    1. 检查依赖（whisper / torch / sounddevice / scipy）
    2. 创建临时文件夹
    3. 调用麦克风录音 5 秒，保存为 wav
    4. 加载 Whisper small 模型，转文字
    5. 打印识别结果
    6. 删除临时文件夹

使用方法：
    cd ai-interview-system
    python scripts/check_whisper_record.py

前置条件：
    1. 电脑有麦克风
    2. pip install openai-whisper torch sounddevice scipy
"""

import os
import sys
import shutil
import time
import tempfile
import scipy

# ============================================================
# 第一步：检查依赖能不能导入
# ============================================================

def check_imports():
    """检查必要依赖是否安装"""
    print("=" * 50)
    print("第一步：检查依赖")
    print("=" * 50)

    # 检查 whisper
    try:
        import whisper
        print(f"  ✅ whisper 已安装 (版本: {getattr(whisper, '__version__', 'unknown')})")
    except ImportError:
        print("  ❌ whisper 未安装，请运行: pip install openai-whisper")
        sys.exit(1)

    # 检查 torch
    try:
        import torch
        cuda_info = f", CUDA: {'✅ 可用' if torch.cuda.is_available() else '❌ 不可用，将使用 CPU'}"
        print(f"  ✅ torch 已安装 (版本: {torch.__version__}{cuda_info})")
    except ImportError:
        print("  ❌ torch 未安装，请运行: pip install torch")
        sys.exit(1)

    # 检查 sounddevice（录音用）
    try:
        import sounddevice as sd
        print(f"  ✅ sounddevice 已安装")
    except ImportError:
        print("  ❌ sounddevice 未安装，请运行: pip install sounddevice")
        sys.exit(1)

    # 检查 scipy（保存 wav 用）
    try:
        import scipy
        print(f"  ✅ scipy 已安装 (版本: {scipy.__version__})")
    except ImportError:
        print("  ❌ scipy 未安装，请运行: pip install scipy")
        sys.exit(1)

    print()


# ============================================================
# 第二步：创建临时文件夹
# ============================================================

def create_tmp_dir() -> str:
    """创建临时文件夹，返回路径"""
    print("=" * 50)
    print("第二步：创建临时文件夹")
    print("=" * 50)

    tmp_dir = tempfile.mkdtemp(prefix="whisper_test_")
    print(f"  ✅ 临时文件夹已创建: {tmp_dir}")
    print()
    return tmp_dir


# ============================================================
# 第三步：录音
# ============================================================

def record_audio(tmp_dir: str, duration: int = 30, sample_rate: int = 16000) -> str:
    """
    用麦克风录音，保存为 wav 文件

    Args:
        tmp_dir: 临时文件夹路径
        duration: 录音时长（秒）
        sample_rate: 采样率，Whisper 推荐 16000

    Returns:
        wav 文件路径
    """
    import sounddevice as sd
    from scipy.io.wavfile import write as wav_write

    print("=" * 50)
    print(f"第三步：麦克风录音（{duration} 秒）")
    print("=" * 50)

    # 检查录音设备
    try:
        device_info = sd.query_devices(kind="input")
        print(f"  录音设备: {device_info['name']}")
    except Exception as e:
        print(f"  ❌ 找不到录音设备: {e}")
        sys.exit(2)

    print(f"  🎙️  准备录音，请开始说话...")
    time.sleep(0.5)  # 给用户一点反应时间

    # 开始录音
    try:
        print(f"  🔴 正在录音...")
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,       # 单声道就够了
            dtype="float32",
        )
        sd.wait()  # 等录音结束
        print(f"  ✅ 录音完成，时长 {duration} 秒")
    except Exception as e:
        print(f"  ❌ 录音失败: {e}")
        sys.exit(2)

    # 保存为 wav
    wav_path = os.path.join(tmp_dir, "test_record.wav")
    # sounddevice 录出来是 float32 [-1, 1]，转成 int16 再存
    import numpy as np
    audio_int16 = (audio_data * 32767).astype(np.int16)
    wav_write(wav_path, sample_rate, audio_int16)

    file_size = os.path.getsize(wav_path)
    print(f"  ✅ 已保存: {wav_path} ({file_size / 1024:.1f} KB)")
    print()

    return wav_path


# ============================================================
# 第四步：Whisper 转文字
# ============================================================

def transcribe_audio(wav_path: str):
    """加载 Whisper small 模型，识别录音内容"""
    import whisper
    import torch

    print("=" * 50)
    print("第四步：Whisper 语音转文字")
    print("=" * 50)

    # 选设备
    device = "cuda" if torch.cuda.is_available() else "cpu"
    use_fp16 = (device == "cuda")
    print(f"  推理设备: {device}")

    # 加载模型
    print(f"  正在加载 Whisper [medium] 模型（首次会下载，约）...")
    t0 = time.time()
    model = whisper.load_model("medium", device=device)
    t_load = time.time() - t0
    print(f"  ✅ 模型加载完成，耗时 {t_load:.1f} 秒")

    # 转录
    print(f"  正在识别...")
    t0 = time.time()
    result = model.transcribe(
        wav_path,
        language="zh",
        fp16=use_fp16,
        initial_prompt="这是一段语音测试。",
    )
    t_trans = time.time() - t0

    text = result["text"].strip()
    segments = result.get("segments", [])

    print(f"  ✅ 识别完成，耗时 {t_trans:.1f} 秒")
    print()

    # 打印结果
    print("=" * 50)
    print("识别结果")
    print("=" * 50)

    if text:
        print(f"  完整文本: {text}")
        print()
        print(f"  分段详情:")
        for seg in segments:
            start = seg["start"]
            end = seg["end"]
            seg_text = seg["text"].strip()
            print(f"    [{start:>6.1f}s - {end:>6.1f}s] {seg_text}")
    else:
        print("  ⚠️  未识别到任何内容（可能录音时没有说话）")

    print()
    return text


# ============================================================
# 第五步：清理临时文件夹
# ============================================================

def cleanup(tmp_dir: str):
    """删除临时文件夹"""
    print("=" * 50)
    print("第五步：清理")
    print("=" * 50)

    try:
        shutil.rmtree(tmp_dir)
        print(f"  ✅ 临时文件夹已删除: {tmp_dir}")
    except Exception as e:
        print(f"  ⚠️  删除失败（不影响测试结果）: {e}")

    print()


# ============================================================
# 主流程
# ============================================================

def main():
    print()
    print("🎤 Whisper 录音 + 语音转文字 完整测试")
    print("=" * 50)
    print()

    # 1. 检查依赖
    check_imports()

    # 2. 创建临时文件夹
    tmp_dir = create_tmp_dir()

    try:
        # 3. 录音
        wav_path = record_audio(tmp_dir, duration=60)

        # 4. 转文字
        transcribe_audio(wav_path)

    except KeyboardInterrupt:
        print("\n  ⚠️  用户中断")
    except Exception as e:
        print(f"\n  ❌ 出错了: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 5. 不管成功失败都清理
        cleanup(tmp_dir)

    print("测试结束 ✅")


if __name__ == "__main__":
    main()