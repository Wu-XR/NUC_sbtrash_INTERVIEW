#!/usr/bin/env python3
"""
测试脚本：摄像头拍照 + Ollama 图像识别
流程：创建临时文件夹 → 拍照 → 发给 Ollama 分析 → 打印结果 → 删除临时文件夹

使用方法：
    cd ai-interview-system
    python scripts/check_camera_and_vision.py

前置条件：
    1. 电脑有摄像头
    2. Ollama 已启动（ollama serve）
    3. 已拉取模型（ollama pull qwen2.5vl:7b）
"""

import os
import sys
import time
import shutil
import base64


# ============================================================
# 第一步：检查依赖能不能导入
# ============================================================

def check_imports():
    """检查 cv2 和 httpx 是否装了"""
    print("=" * 50)
    print("第一步：检查依赖")
    print("=" * 50)

    # 检查 OpenCV
    try:
        import cv2
        print(f"  ✅ cv2 已安装 (版本: {cv2.__version__})")
    except ImportError:
        print("  ❌ cv2 未安装，请运行: pip install opencv-python")
        sys.exit(1)

    # 检查 httpx（调 Ollama 要用）
    try:
        import httpx
        print(f"  ✅ httpx 已安装 (版本: {httpx.__version__})")
    except ImportError:
        print("  ❌ httpx 未安装，请运行: pip install httpx")
        sys.exit(1)

    print()


# ============================================================
# 第二步：创建临时文件夹 + 拍照
# ============================================================

def test_camera(tmp_dir: str) -> str:
    """
    打开摄像头拍一张照片，保存到 tmp_dir 下

    返回照片路径 str，比如 "tmp_test_camera/capture.jpg"
    """
    import cv2

    print("=" * 50)
    print("第二步：摄像头拍照测试")
    print("=" * 50)

    # 打开默认摄像头
    print("  正在打开摄像头...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("  ❌ 无法打开摄像头，请检查：")
        print("     - 电脑是否有摄像头")
        print("     - 摄像头是否被其他程序占用")
        sys.exit(2)

    print("  ✅ 摄像头已打开")

    # 有些摄像头前几帧是黑的，多读几帧让它稳定
    for _ in range(5):
        cap.read()

    # 正式拍一帧
    ret, frame = cap.read()
    cap.release()
    print("  ✅ 摄像头已释放")

    if not ret or frame is None:
        print("  ❌ 读取帧失败")
        sys.exit(2)

    # frame.shape 是 (高, 宽, 通道数)，比如 (480, 640, 3)
    h, w, c = frame.shape
    print(f"  ✅ 拍照成功，分辨率: {w}x{h}")

    # 保存照片
    save_path = os.path.join(tmp_dir, "capture.jpg")
    cv2.imwrite(save_path, frame)
    file_size = os.path.getsize(save_path)
    print(f"  ✅ 照片已保存: {save_path} ({file_size / 1024:.1f} KB)")
    print()

    return save_path


# ============================================================
# 第三步：把照片发给 Ollama 分析
# ============================================================

def test_ollama_vision(image_path: str):
    """
    把图片转 base64，发给本地 Ollama qwen2.5vl:7b，打印分析结果
    """
    import httpx

    print("=" * 50)
    print("第三步：Ollama 图像识别测试")
    print("=" * 50)

    ollama_url = "http://localhost:11434"
    model_name = "qwen2.5vl:7b"

    # 先检查 Ollama 是否在线
    print(f"  正在连接 Ollama ({ollama_url})...")
    try:
        resp = httpx.get(f"{ollama_url}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            print("  ✅ Ollama 服务在线")
        else:
            print(f"  ❌ Ollama 返回异常状态码: {resp.status_code}")
            sys.exit(3)
    except httpx.ConnectError:
        print("  ❌ 无法连接 Ollama，请检查：")
        print("     - 是否已运行 ollama serve")
        print(f"     - 地址是否正确: {ollama_url}")
        sys.exit(3)

    # 读图片，转 base64
    print(f"  正在读取图片: {image_path}")
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    print(f"  ✅ 图片已转 base64 (长度: {len(img_b64)} 字符)")

    # 构造请求，发给 Ollama
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

    print(f"  正在调用模型 {model_name}（可能需要 30-60 秒）...")
    start_time = time.time()

    try:
        resp = httpx.post(
            f"{ollama_url}/api/chat",
            json=payload,
            timeout=300.0,
        )
        resp.raise_for_status()
    except httpx.TimeoutException:
        print("  ❌ 请求超时（超过 300 秒）")
        sys.exit(4)
    except httpx.HTTPStatusError as e:
        print(f"  ❌ Ollama 返回错误: {e.response.status_code}")
        print(f"     {e.response.text}")
        sys.exit(4)

    elapsed = time.time() - start_time
    data = resp.json()

    # 取出模型回复的文本
    content = data.get("message", {}).get("content", "")

    print(f"  ✅ 模型响应成功（耗时: {elapsed:.1f} 秒）")
    print()
    print("=" * 50)
    print("模型分析结果：")
    print("=" * 50)
    print(content)
    print()


# ============================================================
# 主流程
# ============================================================

def main():
    # 临时文件夹名
    tmp_dir = "tmp_test_camera"

    print()
    print("🧪 摄像头 + Ollama 视觉识别 联合测试")
    print()

    # 检查依赖
    check_imports()

    # 创建临时文件夹
    os.makedirs(tmp_dir, exist_ok=True)
    print(f"📁 临时文件夹已创建: {tmp_dir}")
    print()

    try:
        # 拍照
        image_path = test_camera(tmp_dir)

        # 发给 Ollama 分析
        test_ollama_vision(image_path)

        print("✅ 全部测试通过！")

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")

    finally:
        # 不管成功还是失败，最后都删掉临时文件夹
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
            print(f"\n🗑️ 临时文件夹已删除: {tmp_dir}")

    print("\n测试完成。")


if __name__ == "__main__":
    main()

"""

                                                                                                                                 
                                                                                                                                 
                                                                                                                                 
                                                                                                                                 
                                                                                                                                 
                                         l###a                    ###M                                                           
                                         !#M#h                    M#M#                                                           
                                     -#M#m   ^MM##            ##M#    ##M#                                                       
                                     ?###m   ^M#M#            M###    #M##                                                       
                                 ittfjvvvt   'fffftttt    tttftfff    fffftftf                                                   
                                 (M##Qiiil        #M#M    #M##            MM#M                                                   
                                 (#M#Qi!il        ####    ##M#            #MM#                                                   
                                 (##MU   'iiii    M#M#    M##M    >i>i    iii>#MMM`                                              
                                 |###U   `i>i!    ####    #M##    i>i>    iiiiMM#M`                                              
                             x###Xiii;   `ii>i    ##M#MMM#MMMM    >i>i>i>>    #MMM`                                              
                             xM#MXiii;   '>>ii    ####M#MM##M#    i>i>i>i>    M#M#^                                              
                             x###x   ^ii>iiii>iiii'''.''''>>>>>>i>>i>i>i>i    >i>iaM##!                                          
                             xM#Mn   ^iiii>iiiii>i'..'''''>>>>>>>i>i>i>i>i    >i>io##Ml                                          
                         xmmmc/t/+   ^iiiii>ii>iii.'.'''''^^^">>>>i>i>i>i>l!ll`'`'a###qmmm~                                      
                         U###z}}}>   ^i>i>iii>ii>i'.''.'''''''>ii>>i>>>i>>i>>i    a#M#####-                                      
                         U##Mz}}}i   ^>>i>i>ii>iii.'.''''''''`i>>i>>ii>>>>>>i>    a##M#M##?                                      
                     m###n}}}LMMMc::;I>><!''''''''''.'.'''''''''''''''<>>>}}}}M#M#####t[}}m#MM(                                  
                     m#M#x}}}CMMMc;::I<>>!''''''''''.''''''''`''''''''><><}}}}MM#MM#M#/}}}ZMM#|                                  
                     mM##n}}}}}}})\/\[''''`''''''''''''''''''.''''''''''''////}}}}}}}}}}}}ZM#M(                                  
                     mM#Mx}}}}}}})\/\]'''''''''''''''''.'''.'''''''.'''''`////}}}}}}}}}}}}ZMM#|                                  
                     mM######J\\\_'''''''>MMMa`'`''''''''.MMMM#M#M''''''`'''''/\\\*MMMMMMMMM#M(                                  
                     mM#M#M#MJ\/\_''.''''>M#Ma'''''''.'.''#M#MMMM#''.'''''''`'\\/\*MMMMMMMMMM#|                                  
                         U###\''''''']###m   ^ZZZZ''''''.'    mmmmmmmm`'''><>>`'`'`'`'`'''JM#M(                                  
                         U###\'''.'''[#M#m   ^OOOO`'''''.'    mmmmmmmm`''`>><>`'`'``'`'`'`JMMM(                                  
                         U###\''''''']###m   ^OZOZ::::''.'    mmmmmmmm-___())(",",IIII+___OM#M(                                  
                         U###\''.''.'[#M#m   ^OOZO}}}}''..    mmmmmmmm#M###M##<>>>\///k###M#MM(                                  
                         U#M#\'''''''[###m   ^ZZOZ}}}}'.'.    OOOOOZOZ##M#M#M#><>>\///bM#MMM#M(                                  
                         UMMM\'''''''[MMMm   `CCCC{}{}}}{}    OO0O0O00MMMM''''''''><><q###?                                      
                         UM#M\`''''''[M#Mm   `CCCC}{}{}{}}    QQQQ0QQ0M#M#`''`''''>>><qM##?                                      
                         UMM#MMMMY><>-\\\{                        .'''''''''''''''''''m#M#?                                      
                         UM#MMMMMY><>-/\/{                        .''.''''''''''''''''w###?                                      
                         U#MM\'`''`'',>>>}#M#a             ...    ''''''.'''''''''''''mMMM?                                      
                         U##M\''''''`,><<}M##a            .'''..'.'.'.''''.'.'''''''''wMMM-                                      
                         ]tftfjjj};;;I<>>]LLLCftffffff!!!!i!ii:;:;'''''''.;:;:'''':;::qMMM-                                      
                             x#M#X<>>>><>+\\\f########[}[}}}[}<><>'`'`''''>>>>''`'i>>>pMMM-                                      
                             xM##Y>><><>>+/\/t#M#M##M#}[}[}[}[><>>`'''''''>>>>''''i>>>pMMM-                                      
                             xMMMX<<<<>><+\\/\/\\\M###}}}}iiii''''.'''>>>>\\\\>>>>oMM#!                                          
                             xM#MY<<><>>>+/\\\\/\/####}}}}iiii''''''''>>>>\\\\>>>>o#MM!                                          
                                 |###0><<>>><</\/\#M#Mi>i>iiii}}}}&&&&WWMM\\\\\\\\*MMM!                                          
                                 (#M#Q<>>><>><\\\/####>i>iiiii}}}}&&&&WWMW\\\\\/\/*MMM!                                          
                                     -#M#b\/\f#M##    iiii            }}}}MMMM\/\\*#M#!                                          
                                     -M##k\\\f##M#    iiii            }{{}MMMM\\/\*M#M!                                          
                                     ?###*pppw~~~+    ````        _+__}}}{jjjrddpdcvvvCQQQ<                                      
                                     -M#M##M#a                    }}}}}{}{}{}}MMMMf\//kMMM-                                      
                                     ?###M##Mh                    }}}}}{}}}{}{MMMMf//\bM#M?                                      
                                     -MMMqiii!                !!!!M#MMM#MM        a#MMM#M#?                                      
                                     ?M#Mqiii!                !l!lMMM#M#MM        aM#M#MMM?                                      
                             x#M#####Qiii[MM#o!!!!!!!!!!!!!!!!!!!!l!l!MM#MM#MM        mM##MMM#(                                  
                             x###M#M#Qiii[MM#o!!!!!!!!!!!!!!!!!l!!!!!!#MM#MMM#        mMMM##MM(                                  
                             xM##muuuunuuY#M#o!!!!!!!!!!!!!!!!!!l!l!l!M#MM[}[}            JM#MMMM#n                              
                             x#M#wunuuuunYMMMa!!!!!!!!!!!!!!!!!l!l!!!lMMMM}[}[            UMM#M#MMx                              
                             x###muunuunuununcM#MM    !i!i        M#MM}}}}}}}}}}}}'       J#M#C/\/JMM#M#MM#MM#a                  
                             xM##muuunuuuuuuuvMM#M    iiii        M#M#{}{}}}}}}}}}'       JMM#J//\JMM#MM#MM#MMa                  
                             x##Mmuuuuuuuuuuuv*o**llll????lIlIIlIlMMMM}}}{}{}}{}{}'   liiiYkbkY\//YbkbkbkbhM##a                  
                             xM##mnnuuuuuuuuuvmmmmmmmmmmmmmmmmmmmm##M#}}}}}}}}}}}}.   m#M#z//\///\//\/////nMMMa                  
                             x#M#munuuuuuuuvuvmmmmmmmmmmmmmmmmmmmmMMMM}}}}}}}}}[}}'   mMMMz/\//\//\//\/\/\n#M#a                  
                                 |####MMMMMMM#mmmmmmmmmmmmmmmmmmmmM#MM}}}}}}}}}}}}oM#Mn/\/\/////\/////zMMMm                      
                                 (M#M#M#M#M#M#mmmmmmmmmmmmmmmmmmmmMMM#}}}}}}}}}}}}oMMMn\//\/\/\///\//\z#M#m                      
                                         !#MM#mmmm####mmmmmmmmmmmmMM#MMM#MM#MM#M#Mf///kM#MMMM#MMMMM#MMU                          
                                         !MM##mmmm#M#MmmmmmmmmmmmmMM#M#MMM#MM#MM#Mf///k#M#M#MM#M#M#M#MU                          
                                         !#MMo}}}}M#M#mmmmmmmm}}}}[}}}M#MM/\//////////bMMM#M#M|                                  
                                         !M#Mo}}}}#MMMmmmmmmmm[[}[}[}[MM#M//\/\\/\\/\/bM#MMMM#|                                  
                                     :(((tCCCCuuuuWWMWkbkb/\\\>ii>[}}}M#M#JJJJ////////CO0Oh#MM(                                  
                                     -M#Md[}}1dddd&&WWMMMM        }[}[MMMMMMMM/\/\/\/\////qMM#|                                  
                                     -###d}[}{dddd&&WWWMM#        }}[}M##M#M#M\/////\/////q#MM(                                  
                                     ?#M#*dddpvuuu&&&&MMMM            ii>i#M#MM#M##MM#MM#M?                                      
                                     -###*dpdpuuuu88&WWMMM            i>iiMMM#MM#MM#M#M#M#?                                      
                                     ?#M#huuuc8888&&&&WWMM                M#M#                                                   
                                     -M##huvuc8&8&&8&WWWMM                M#MM                                                   
                                     ?#MMW&&8Wuvvv8888&&WWWMMM            MM#M                                                   
                                     ?MMMW&&&Wuvuv&8&8&&&WWM#M            M#M#                                                   
                                 -UUJZWWW*LQLQkkkk\/\/WWWWMMM#            \\\\UUUU'                                              
                                 (#MMWW&8*vuvc8&88iiiiM#M#M#MM            i>i>#M##`                                              
                                 (#MMW&&&*uvvc88&8!ii!MM#MMM#M            >i>>###M^                                              
                                 (#MWW&8888&8#iiiiiiii#MM#M#M#                M###`                                              
                                 |#MMW&&88888#iiiii!ii#M#MMM#M                ##M#`                                              
                                 (M#MQiiiiiiiiiii!uuuuMMM#M#MM                #M##^                                              
                                 (MMMQi>i>i>iiiiiiuvuuM#MM#MM#                ###M`                                              
                                 (MM#duuuuuuuvuuuuuuuuMM#M    ####        }}{}{{}}*MMM!                                          
                                 (M#MduvuuuvuuuuuuuvuuMM#M    #M#M        }{}}}}{}*MMM!                                          
                                 |#MMpuuuuuuuuuuuuunuu#MM#    M#M#}}}}}}}}}}}}}}}}*MMMl                                          
                                 |M#MdnunuunuununuuuuuMM#M    MMMM}}}}}}}}}}}}}}}}oMMM!                                          
                             `:::fMM#duuuuuuunuuuunuuu#MMM    M##M}}}}}}}}}}}}}}}}*MMM!                                          
                             xMMM#M#MpuuununuuuunuuunuM#M#    M#M#}}}[}}}}}}}}}}}}oMMM!                                          
                             xMM#MMM#dnuuunuuunuuunuuuM#MM    MMMM}}}}}}}[}}}}}}[}*MMM!                                          
                             xMM#wuuuuuunuuuuuuunuM#MM        M##M}}}}}}}{}}}}}}}}*MMMl                                          
                             xM#Mmuuuuunuuunununuu#M#M        MMMM}{}{}{}}{}{}}}}}oMMM!                                          
                             xMMM#MMMM#MM#M#MM#M#M            #M#M}}{}uuuu{}}{unuu*MMM!                                          
                             xM#MMM#MMM#M#MM#MMMMM            MMMM}{}{uuvu}}{}uuuu*MMM!                                          
                                                              M#M#MM#MMMM#MM#M#M#M#MM#!                                          
                                                              MMMMMM#M#M#M#MMM#MMMMM#M!                                          
                                                              xxxxxxxxxxnxxxxxxxxxxxxx"                                          
                                                                                                                                 
                                                                                                                                 
                                                                                                                                 
                                                                                                                                 
                                                                                                                                 
                                                                                                                                 
                                                                                                                                 
                                                                                                                                 
                                                                                                                                 


"""