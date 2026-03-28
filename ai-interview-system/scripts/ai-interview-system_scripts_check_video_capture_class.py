#!/usr/bin/env python3
"""
测试脚本：验证 VideoCapture 类能不能正常工作
流程：创建临时文件夹 → 用 VideoCapture 类拍照 → 用 llm_client 的方式分析 → 删除临时文件夹

使用方法：
    cd ai-interview-system
    python scripts/check_video_capture_class.py
"""

import os
import sys
import shutil

# 把项目根目录加入 Python 路径，这样才能 import app.core.xxx
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    tmp_dir = "tmp_test_class"

    print()
    print("🧪 VideoCapture 类功能测试")
    print()

    # ============================================================
    # 第一步：看能不能导入这个类
    # ============================================================
    print("=" * 50)
    print("第一步：导入 VideoCapture 类")
    print("=" * 50)

    try:
        from app.core.multimodel import VideoCapture
        print("  ✅ VideoCapture 类导入成功") # 现在还无法导入的就是，因为python的机制，再app全部写完之前，这无法导入
        # 但是我基本环境是成功的，所以其实也不用管来着
    except ImportError as e:
        print(f"  ❌ 导入失败: {e}")
        sys.exit(1)

    print()

    # ============================================================
    # 第二步：创建实例，指定临时文件夹
    # ============================================================
    print("=" * 50)
    print("第二步：创建 VideoCapture 实例")
    print("=" * 50)

    try:
        camera = VideoCapture(camera_id=0, save_dir=tmp_dir)
        # camera.save_dir 应该被赋值成 "tmp_test_class"
        print(f"  ✅ 实例创建成功")
        print(f"     camera.camera_id = {camera.camera_id}")
        print(f"     camera.save_dir  = {camera.save_dir}")
    except Exception as e:
        print(f"  ❌ 实例创建失败: {e}")
        sys.exit(2)

    # 检查文件夹是否被自动创建了
    if os.path.exists(tmp_dir):
        print(f"  ✅ 目录 {tmp_dir} 已自动创建")
    else:
        print(f"  ❌ 目录 {tmp_dir} 没有被创建")
        sys.exit(2)

    print()

    # ============================================================
    # 第三步：调用 capture_frame() 拍照
    # ============================================================
    print("=" * 50)
    print("第三步：调用 capture_frame() 拍照")
    print("=" * 50)

    try:
        # 不传 filename，测试自动生成文件名
        photo_path = camera.capture_frame()
        # photo_path 应该被赋值成类似 "tmp_test_class/1711612800.jpg" 的 str
        print(f"  ✅ capture_frame() 返回: {photo_path}")
        print(f"     返回类型: {type(photo_path).__name__}")
    except RuntimeError as e:
        print(f"  ❌ 拍照失败: {e}")
        sys.exit(3)

    # 验证文件是否真的存在
    if os.path.exists(photo_path):
        file_size = os.path.getsize(photo_path)
        print(f"  ✅ 文件存在，大小: {file_size / 1024:.1f} KB")
    else:
        print(f"  ❌ 文件不存在: {photo_path}")
        sys.exit(3)

    print()

    # ============================================================
    # 第四步：传自定义文件名再拍一张
    # ============================================================
    print("=" * 50)
    print("第四步：指定文件名拍照")
    print("=" * 50)

    try:
        photo_path_2 = camera.capture_frame(filename="test_photo.jpg")
        # photo_path_2 应该被赋值成 "tmp_test_class/test_photo.jpg"
        print(f"  ✅ capture_frame('test_photo.jpg') 返回: {photo_path_2}")
    except RuntimeError as e:
        print(f"  ❌ 拍照失败: {e}")
        sys.exit(4)

    if os.path.exists(photo_path_2):
        file_size_2 = os.path.getsize(photo_path_2)
        print(f"  ✅ 文件存在，大小: {file_size_2 / 1024:.1f} KB")
    else:
        print(f"  ❌ 文件不存在: {photo_path_2}")
        sys.exit(4)

    # 检查目录下应该有 2 张照片
    files = os.listdir(tmp_dir)
    print(f"  ✅ 目录下共 {len(files)} 个文件: {files}")

    print()

    # ============================================================
    # 第五步：把照片发给 Ollama 分析（模拟 llm_client 的调用方式）
    # ============================================================
    print("=" * 50)
    print("第五步：用 llm_client 的方式分析照片")
    print("=" * 50)

    import base64
    import httpx
    import time

    ollama_url = "http://localhost:11434"
    model_name = "qwen2.5vl:7b"

    # 读取 capture_frame() 返回的路径，转 base64
    with open(photo_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "请分析这张图片中人物的面部表情、坐姿、眼神方向，用中文回答",
                "images": [img_b64],
            }
        ],
        "stream": False,
        "options": {"temperature": 0.3},
    }

    print(f"  正在调用 {model_name}...")
    start_time = time.time()

    try:
        resp = httpx.post(f"{ollama_url}/api/chat", json=payload, timeout=300.0)
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "")
        elapsed = time.time() - start_time
        print(f"  ✅ 模型响应成功（耗时: {elapsed:.1f} 秒）")
        print()
        print("  模型分析结果：")
        print("  " + "-" * 40)
        for line in content.split("\n"):
            print(f"  {line}")
        print("  " + "-" * 40)
    except Exception as e:
        print(f"  ❌ Ollama 调用失败: {e}")
        print("  （不影响 VideoCapture 类本身的测试结论）")

    print()

    # ============================================================
    # 清理
    # ============================================================
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
        print(f"🗑️  临时文件夹已删除: {tmp_dir}")

    print()
    print("✅ VideoCapture 类测试全部通过！")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        # 中断了也要清理
        if os.path.exists("tmp_test_class"):
            shutil.rmtree("tmp_test_class")
            print("🗑️  临时文件夹已删除")