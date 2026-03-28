#!/usr/bin/env python3
"""
测试脚本：临时文件夹 → 录音 → Whisper 语音转文字（对比有无提示词效果） → 删除临时文件夹

流程：
    1. 检查依赖（whisper / torch / sounddevice / scipy）
    2. 创建临时文件夹
    3. 调用麦克风录音 30 秒，保存为 wav
    4. 加载 Whisper small 模型
    5. 第一次：不带提示词识别
    6. 第二次：带提示词识别
    7. 对比两次结果
    8. 删除临时文件夹

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

# ============================================================
# 第一步：检查依赖能不能导入
# ============================================================

def check_imports():
    """检查必要依赖是否安装"""
    print("=" * 50)
    print("第一步：检查依赖")
    print("=" * 50)

    try:
        import whisper
        print(f"  ✅ whisper 已安装 (版本: {getattr(whisper, '__version__', 'unknown')})")
    except ImportError:
        print("  ❌ whisper 未安装，请运行: pip install openai-whisper")
        sys.exit(1)

    try:
        import torch
        cuda_info = f", CUDA: {'✅ 可用' if torch.cuda.is_available() else '❌ 不可用，将使用 CPU'}"
        print(f"  ✅ torch 已安装 (版本: {torch.__version__}{cuda_info})")
    except ImportError:
        print("  ❌ torch 未安装，请运行: pip install torch")
        sys.exit(1)

    try:
        import sounddevice as sd
        print(f"  ✅ sounddevice 已安装")
    except ImportError:
        print("  ❌ sounddevice 未安装，请运行: pip install sounddevice")
        sys.exit(1)

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
    """
    import sounddevice as sd
    from scipy.io.wavfile import write as wav_write
    import numpy as np

    print("=" * 50)
    print(f"第三步：麦克风录音（{duration} 秒）")
    print("=" * 50)

    try:
        device_info = sd.query_devices(kind="input")
        print(f"  录音设备: {device_info['name']}")
    except Exception as e:
        print(f"  ❌ 找不到录音设备: {e}")
        sys.exit(2)

    print(f"  🎙️  准备录音，请开始说话...")
    print(f"  💡 建议说一些包含专业术语的内容，比如：")
    print(f"     \"我觉得 Spring Boot 的自动配置原理是基于条件注解\"")
    print(f"     \"Redis 的持久化方式有 RDB 和 AOF 两种\"")
    time.sleep(1)

    try:
        print(f"  🔴 正在录音...")
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        print(f"  ✅ 录音完成，时长 {duration} 秒")
    except Exception as e:
        print(f"  ❌ 录音失败: {e}")
        sys.exit(2)

    wav_path = os.path.join(tmp_dir, "test_record.wav")
    audio_int16 = (audio_data * 32767).astype(np.int16)
    wav_write(wav_path, sample_rate, audio_int16)

    file_size = os.path.getsize(wav_path)
    print(f"  ✅ 已保存: {wav_path} ({file_size / 1024:.1f} KB)")
    print()

    return wav_path


# ============================================================
# 第四步：Whisper 转文字（支持传入提示词）
# ============================================================

def transcribe_audio(wav_path: str, model, device: str, prompt: str = None) -> dict:
    """
    用已加载的模型识别录音

    Args:
        wav_path: 音频文件路径
        model: 已加载的 whisper 模型
        device: 推理设备
        prompt: 提示词，None 表示不用提示词

    Returns:
        {"text": "...", "segments": [...], "time": 耗时秒数}
    """
    use_fp16 = (device == "cuda")

    label = f"提示词=\"{prompt}\"" if prompt else "无提示词"
    print(f"  正在识别（{label}）...")

    t0 = time.time()
    result = model.transcribe(
        wav_path,
        language="zh",
        fp16=use_fp16,
        initial_prompt=prompt,
    )
    elapsed = time.time() - t0

    text = result["text"].strip()
    segments = result.get("segments", [])

    return {"text": text, "segments": segments, "time": elapsed}


def print_result(result: dict, label: str):
    """打印一次识别的结果"""
    print(f"\n  【{label}】（耗时 {result['time']:.1f} 秒）")
    print(f"  {'─' * 46}")

    if result["text"]:
        print(f"  完整文本: {result['text']}")
        print()
        print(f"  分段详情:")
        for seg in result["segments"]:
            start = seg["start"]
            end = seg["end"]
            seg_text = seg["text"].strip()
            print(f"    [{start:>6.1f}s - {end:>6.1f}s] {seg_text}")
    else:
        print("  ⚠️  未识别到任何内容")

    print(f"  {'─' * 46}")


# ============================================================
# 第五步：清理临时文件夹
# ============================================================

def cleanup(tmp_dir: str):
    """删除临时文件夹"""
    print()
    print("=" * 50)
    print("清理")
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
    import whisper
    import torch

    print()
    print("🎤 Whisper 录音 + 提示词效果对比测试")
    print("=" * 50)
    print()

    # 1. 检查依赖
    check_imports()

    # 2. 创建临时文件夹
    tmp_dir = create_tmp_dir()

    try:
        # 3. 录音 30 秒
        wav_path = record_audio(tmp_dir, duration=60)

        # 4. 加载模型（只加载一次，两次识别复用）
        print("=" * 50)
        print("第四步：加载 Whisper medium 模型")
        print("=" * 50)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"  推理设备: {device}")
        print(f"  正在加载（首次会下载，约 461MB）...")

        t0 = time.time()
        model = whisper.load_model("medium", device=device)
        print(f"  ✅ 模型加载完成，耗时 {time.time() - t0:.1f} 秒")

        # 5. 对比测试
        print()
        print("=" * 50)
        print("第五步：对比识别（同一段录音）")
        print("=" * 50)

        # 第一次：不带提示词
        result_no_prompt = transcribe_audio(wav_path, model, device, prompt=None)
        print_result(result_no_prompt, "无提示词")

        # 第二次：带提示词（你可以根据你说的内容改这里）
        tech_prompt = "刚刚，一群squad游戏玩家（硬核仿真）结束了一场失败的任务，其中，一个队长对“重筒”（就是反坦克武器）的分配产生了矛盾"
        result_with_prompt = transcribe_audio(wav_path, model, device, prompt=tech_prompt)
        print_result(result_with_prompt, f"有提示词")

        # 6. 对比总结
        print()
        print("=" * 50)
        print("对比")
        print("=" * 50)
        print(f"  提示词内容: \"{tech_prompt}\"")
        print()
        print(f"  无提示词: {result_no_prompt['text'][:80]}{'...' if len(result_no_prompt['text']) > 80 else ''}")
        print(f"  有提示词: {result_with_prompt['text'][:80]}{'...' if len(result_with_prompt['text']) > 80 else ''}")
        print()

        if result_no_prompt["text"] == result_with_prompt["text"]:
            print("  📌 两次结果完全一致（录音中可能没有容易混淆的专业术语）")
        else:
            print("  📌 两次结果不同，提示词影响了识别结果，请对比上面的文本看哪个更准确")

    except KeyboardInterrupt:
        print("\n  ⚠️  用户中断")
    except Exception as e:
        print(f"\n  ❌ 出错了: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup(tmp_dir)

    print("测试结束 ✅")


if __name__ == "__main__":
    main()