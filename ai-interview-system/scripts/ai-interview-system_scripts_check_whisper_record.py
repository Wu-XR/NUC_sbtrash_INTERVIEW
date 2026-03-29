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
        tech_prompt = "这是Linux系统面试，将会问一些关于Linux进程相关的问题"
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

"""

                                                                                                                                                                                                                
                                                                                                                                                                                                                
                                                                                                                                                                                                                
                                                                                                                                                                                                                
                                                                                                                                     'YYn}:                                                                     
                                                                                         ;fY+                                        fY'"x0j`                                                                   
                                                                                       IuY}_C-                                      !U^   lYv                                                                   
                                                                                      !J-   !x                                      ;!      f-                                                                  
                                                                                     `t>     f<                                              ?                                                                  
                                                                                    ~Z~      <Y                                    >u"       .;                                                                 
                                                                                   _Ql        c]                                  +Q~         }                                                                 
                                                                                  <Q[         ,(                                 lC-          ?[                                                                
                                                                                 ^Yj           {(                               iw}           I/                                                                
                                                                                 1UI           "n-                             .J)'            1`                                                               
                                                                                "L(             ivI                            u\..            :I                                                               
                                                                                xL!             '?n                           jv,.              ,                                                               
                                                                               lQu'              ^rX                         jY:.               `,                                                              
                                                                               1Z+               ';Lv                       /O_'.                +I                                                             
                                                                              :CJ                 .lQx                     -Of`''.               ~zuvuj\-,                                                      
                                                                  ^l?\xvYXzczvJmj                 .']m/                   `zL^''..             ,|i)/, 'I]rLc[`                                                  
                                                               ,<QX\_l`'     ?0(;?)"              .."tZ[                  [0<'.'.                 ;ci      ,];_i                                                
                                                            l\U1             rL    "`               .;cZ>         !v,    "Xu`.'.                  'rn         >Yr;                                              
                                                          I}1;              >L?                      .+LL,         /u`   ?w+...                    }Ui          <\?                                             
                                                        'tvl                /X.                      .^{mj'        }0\  .rL:'.'.                    J{           '{('                                           
                                                        ?C+                :Of                        .,fZ{       ^U[x> ,z[  ....                   cX.           'tj^                                          
                                                        \Y!                1Zi                         .IYO?      {X:(j`>Y<                         {C;            :Q}                                          
                                                        lCul            "<|YC/()l                       .>0z,    }r,")u"+u:                     >}/||0[:           ./z                                          
                                                         `)QJ1!^.   'l[xJXCwc                        '^,:lfmJJv\r>"""|\fur/tt(i               nx"   ~mJYOz_        'nn
                                                            ;_(\/|{>/nvj|[)Ot                    l11?!I;_}l'  ':;,,;+i,^'     ;1r_           i<     +OX(+_?~u?    ^|0+
                                                                .I^`      <O)                 Ir|,     "        ':;:"            !v}                _Zf)t\({|Uz[?r0X;
                                                               `1/'       +0l              Ij{^      `                            .<x<              ]QI   ,!+}{1{1;
                                                              :}<         +Q;            _n~        ,                               `\/             rC"         `_?`
                                                             >jl          <0l          ?u,        ,i                       .          ~[            Jj            -zI
                                                            !U+           ;U}        I\!         ^<    `'.      .          '`.         .'          ]J>             1L!
                                                           `vz`        'i1?rx       {{    '     '?,   "^`'                   `'          ."       ^ujl             ^X|
                                                           .Xz"     "<?][I"_t,    "|I    '      >+``'",``'     .'''``^``'`'   '            l'     ~/-zx()1<        `nx
                                                            :uUxfrur|]i` ,\1`    "}`   '.      "},`'^:,^'.   .````^^"^"^``.   :^            i;       ."}znr-l^    lt0<
                                                              ',:,^.`~-I"        t'   .        !+`^',,,^`'  '"^",,"^^^"`      I! .'          l>       ~0O?!?xnzLwmC}'
                                                                    .)rxunf],   (`   '     .  .]l^^`,,""`   ''`^`'`  .^    ' '"+^ ..          >-     fX+
                                                                               !!   .     .'```\l"``,"""'            ^"^^,,,,,^_I.:'.          >?   -t`
                                                                                   ''    '`^"""(l"^^","":::;;;I:"". ^,""",",,,^[> i;            ?x<
                                                                          ;(+'    ^"   '^^"""^")+:"",,:,:,:;:;;:,,","","",",""^f< ^|:       .    [\r~
                                                                         rj      `"`  '^,"""""^<tI,,,'',,,::;:,I:"^^""""""""".lc^  lx'       .    [`_L[.
                                                                       _v! 'I   '^"''.^","""``'"f~:,'   '`,::,,I'   '`'. .`' .)|    lxI      '    I)  <uj+`
                                                                     .ru`  <`   `""`'`^"^`''.  ^x+,`      ,~;,;i         !n+^>j;I!(uzCZU1.   '".   ]<    ~nUzr|)\n?
                                                                    lC!   ;-   '^,^'``^^`!1fnzCOmQLLJJJJCQjI,:l>          `<XLu\+!;     /u"   .^'   1.          ft'
                                                                   ;{    "|i   '^,"'``^`       ln^'I:        `!_          '[- '";;Il;".'cXI;<:'`^`` !l        iX1
                                                                  ,?`   "If^  .'^,^'`''.   `^''c[^,:-}i'      `<         ":;  ^I+nQwwqwYqQCw0_",,""""+      <Cf"
                                                                 ^tl  '^"]|.  .`""-0Oz|+(0qqqqqmXf[~~[\1>^     i`     ``^'>"^+vZmwqwZZwmZQm/"ll,""^""rY(<}vJ(,
                                                                 ]t"  `""]).   '^^ `\ZqqqqqpqwwmqOYC0Jcf\[I    ^:        +<>XZ0OLJJJuunQmm}'^,-;"^""^10/{+`
                                                                `rf  ^"",](     ^`   `fwqLmOL0ZmmmCYYuQqqmX~^   ^;.     f?|v~~cZqqqc:.>JqY]>^"+-^^`^^^rr`
                                                                "CY..""""!]     ^`  ^;_Lq|_<i?cj}0LJZzXvc0LOv~`  ''   <f;XmJwmCuj|n|  "CwmX?"";}````'''fx,
                                                                .tm}.",;'^[;    `"  >nmqqJ   !f(cwOZX)1])Qi I1)  ,  iui`Q_rqwzft\\U`  ;wv" .'.'[^'``'  .cu"
                                                                 ~OY;":I. ":    `^    ^zjJ:  'f(1(/(1)1-|J      `}}?`  `0cXv|[})u)    !|"     '].       IO{
                                                                  }mu:^;.  '    l,.   `ni     ;0/~++?1])/,              |f}?-[tCv'    !ZQ1i,. :~         cQ;
                                                                   Ij0z?        <^     /j `'   +0Y([}/U0!          !++''<+vLLx~.     _JwOOOmc"i'         >m|
                                                                       [j},    "+'     (z  ;-:   :})1_'     +_;   :(]_~i?/z+'    `+nQfJQ?l. .:;       .   {C~
                                                                        `tl    l+      [Y' Icwqxi      .^l|Jr]    !]~~-<;,1UwmmwZCzjt-wv~!  'I^       .    >Y+       >i
                                                                     tC0Jf[    !+      ,zXUJUXnrzCOOOO0CXcx|i       i<++i ~XXzYcvXYf>uz?n~  .""             ,|jI   ljun'
                                                                       '}[    '!<      'X_[_"1Ycnxrxxxxnuj-'        `>_1|:  ,1//(+, ?U"?xI   ^,     '`'        "+/\! n)
                                                                  !!+|cf;'`   `!<       1t +>  _nCJYYzx)i'           '\Y-          +X>,jr,   `:.    `"              {v^
                                                                  `>[1\fY|    ";<       iQ  !?  `^;!!,.                           )X<,,u\'   ^:^    ::           :}LU!
                                                                       ]L_    ^"i"      'Yvi  ~:        ^             .         :Orl,"!Y,    ^;"    }I          (Qx+
                                                                      "uU`    ';ll'      \J>}!^'        uYU{`^[fr/\1uJ)       "nu>::,`C(    ',:".  ?f        Il"ju,
                                                                      _O\      l;I"       Z1;?/~'         `n[' `'  ?c^      Izzi:::,;cu^   '","^''_u'     '~\!  c|
                                                                      1w?      ;!,I^      _Yl!}CZz(l^       ./:         '+nY|!;::;,iX\`   ^:;,"">/|^'`"i}j):  -Lf`
                                                                      (w?      `>;`I:      n|;I)ZJ?+zZCr}l"^'    '!}\vLCx]!;;;:::,\J_.  'li]xf\({|]  "{},;{jxj{,
                                                                      }wn      .;I".,>'    <Z_::(w/:iXqqqwqqqqqqqwQx[++~+_+_~<!i1w('  "~?!"'!u;   {}  \|
                                                                      ILZ?      ,:"  .;i"   1j;lzL<;I;+JwwOmqqCr{+<!!llllll~]tYC|I!~?]_;`    }x'  'nl,L<
                                                                       ~0O(     '""'   '"l<!,{(1_   "I;;OqqqwCtfucccx\}~<{uQwZUj{<:'         'v/  IY0C_
                                                                        lnm01'   ^```   ^   ^cc}      ",~0qZLOLQX}_?|cLmOCr|1(/j00|`          1Zi  '
                                                                          ^-vQJ|` ^I,  Ifu   I?|I      ``"?rQw0Y}      :n__]1))))/UZ1         iZ\
                                                                              :tz_>,;?Cwc<,  ' .}-             ]!    .  :u1{((|\|||rmt         Ju
                                                                              )U?_}zC\i.  ,'  l^-!:            +^    ""  iY\(|\tt<(|tOn        Uu'
                                                                             _0X0wJ;       ,'  i    [         'j,     I`  ~c(|\//\\\|tU~       Lf
                                                                           ,[cmqwf1_        ^" 'i   )|        ~/'      <  '(j(\/\//\\|\f      <O}
                                                                        :[n0mQr{:  ]{                ,]"    ;<\!       I,  ,c\////\/\)}f;     fC^
                                                                    ^~(zOwwf'  )^   +c                   I c[1v1       "I   [X}1)|()11{j-    _L<
                                                                'i}rJZw0v}>l:` }!    'f,                 I>j.` ],      ,;    >f][}11{[-||.  !u[
                                                              ,1XZZUx|1}}[[-~i:[+      (-                ]'\.. _l      ;:      {)__+_++?}, "(_
                                                             -Omc()()())1{}}]_i1J       i\              ,~"1:^ _;      >        "v]+~~~~{[`;|-
                                                            i0mx()()())()(1}[?+{C        'ul            "{;)nfj(       >          ~zz(_!~vnI>fr-I
                                                            tqL\|(}|(((())){}]_[J          1+             "           <'            ^{QOjijx{{(/_
                                                           'jwX|\}{\|(((())1{]+iX           ;1'                      ;!                `}YZCf:
                                                           "0mr(|]\|(|(((())1]~iY^            :~                    :l                    :(LC{'
                                                           Iwmf(){||(|(|(())}-~lY"               ;'                >,                       `?J0)'
                                                           ,mmn()(||(|((((){]-_IY:                  .           `:^                           "|QC_
                                                            /mz|(||(||||(1{[]?xfC{                                                              `|Or"
                                                            !LJ||||(|||){}}}]+i)O{.                                                               >C0-
                                                            .jL\((((()11{{}[-~!`z!                                                                 !JZ1
                                                             {L\{{{{111{1{}?_>: XI                                                                  !CZ[
                                                             ]Lt{{11111{{}[?+! ^z                                                                    +mU:
                                                             }Qj{{1111{{}[?+i, _v                                                                    .jw[
                 l^                                          }Qt}{1{{{}[[?+>!  {l                                                                     ]m}
                ^- !:                                        [Q\]][[[[[[-+>!"  z"                                                                     -Z[
                f:  '_{^                       Ii+_~i,       -Q(_??]]]?_<i!:   U^                                                                    `UX,
               Iz      "1|l             ;{cj)<.     ,)Xm0u]:^+Q(!i~~~<>i!I;'  `t                                      "l<~+]!                       ,UJ!
               t_          ~\)i      >r1^                -vOw0Qt;;IlllII;,"   ,|                                  ^I!I" '~-^                      '_Ou,
              .z"              '^"ll:`                      '?Zn,",,:::,,^.   ]\                               `::`   '_]"                     . :uQ[`
              lQ"                                             ]j,^^""""^`     [}                              ''    '-{:                      ',rZtl|,
              "z-                                             ;xI  ''.        ]{                                   _1l    .         ..'.'.'',<?Qv'  t|
              'xY                                              1:             ]|                                 <(~`.`""`''       .'`'^;+[[<^!-    +x^
               IQ-                                             <~ izZCCw(     ;\                               l({I;;,`          `^^`.        >Z(   `\+
                !rI                                            l\(U;`"}Q>      Y"                            ;1)+l;`                            <(rxYYzz/l
                 l;                                            \<~U:;|Ql       tu                         ."[/-:'                                 `I/CujCOji
               :|!                                            :\;:x?rY'         Yv^                    .'",,"`                                  .(U|`   '/mU?^
              _\,                                             `];l\Q}            {C{                '`^":".                                   -Xf>^       "cJ_
             1f`                                               IizL"               tZC;         .'`"","                                   `?(|.             nC>
            1t^                                                 ;|u                  ljcc{^    `^``                                     >num}               ^JUl
           |r^                                                   ~u                 `Q1   `                                          :I`'' UX                >mUl
          {Y^                                                    ~z                "L(                                            ;?I '^'  JCl                cpx^
         _c"                                   ''                <z               ,\>                                          >[+^ '^'     ,fU_              -qQ-
        !Y?                             .'.  '`"^'               iz              tmU:                                       tU]  `""'         ,Qz       ">~<l  Uwu,
       `x|'                           .`^""` ":;,`               lY'                I//>                               ;{ur~`^^""`'             |Q_<{fjrnr/\xc0vmC]
       }c,                            `;::,`.:IlI^               ;Ci                   'cLf!                      `itvn?:^"","^'''. .            }L-^.'`.      `tZr:
      ;Q?                             ^-?;,``:i!l,.              `J}     .`^"""^^'      [C ;\I               icL0X~;"^'  `|l,"^'''.'..            )Q,`^'    ;i; `CU[
      vX"                             `?[::"^:>!!l".             .J}    `":::::,,"^`.   |0,;I!~-1|tjxuczznt1?i,^`        _Oi,"`''.'''.'.          `zu^`  "~<^    <Ov;
     _Z}                         .     ;)i:,,;<iii!,              X(  '",;IIIIII::,^^'  cx   `",,",,,,,""`.             IC/;""^`^``''''..          <O_^l+i        \m|'
     xQ                      .   '      +}!:::>i!ii;'             ux..":;ll!iii!!I;,^`'iL<                              Yr?!,,,:,,""``'''.          vU~!  `Il;^:;^`XQ_
    :L1                      .   .       _}+iIl<>>ii,.            +Y,^:II!><<~<<>>!I:^"/U`                              .?x!,`  ,,,,^''''           +O?. ,){,      ;ZXl
    )Ql                     .   '.        :_{([-+>ii!;^           ;Qi:;l!>~+++~~<<i!I,>Q)                 .'''.'.        .!~:,",,,,"^`'''           'UJ|Lwqj`       >wYl
    xz^                     '   `            'l[|)+i!lI:``'.      :Q};I!i~____~~<<>il:)Q>                .''''''''.'.....'`,:,,::,,"`''''   `      ^:?OL{LJ,         \qUl
   "zj                      `   ^                .i>!llI;,,^`'     jt;l!>+---__++~>!llux'              .''''''''`'''''''''`":,,,,,^```'''   :    ":,,,ivZwi.         "QqU,
   ICf                     .'   ^                  !>!!!II;;;,^'  `nzi!i<_-?---_+~>!I<0[              .'.'.'''`'''`'`'''''```"","```'''''  `I  .''"_vOwwmqQ+         !xvqj
   lCj                     ''   "                   "<~>!l!l;II+|CLvL+!i+??-???-+~<!l[Q!       .'     .'.''''''''`'''`'''`'``````'`''.'.   !"`I]jOZJvrxunOqZ-  ,}rCQCur{ZUI
   !Cj                     '.   "                     ^i-]ummwwz], ^J}!>_-?????-_+~>lYcz0zt"   `,'    ..'.'.''''''`'`'''``^`'`''''''...  .tY0mLcvxnQYCUcvuYqwnfU(l;l_)XnOO+
   lJn'                    `    "                 .''`"",:;Il?jr<   fCi~--?????-_++>iZXjjuz0wqqCu},    '.'.''''''''''''''''''''''.""l}xQmOUxrxxxLXUmcnnzQcrYwwz_`  ^",,;zm)
   ,XY"                    '    "                '``",:;;;IIlI;l)x_ [Z?+-??]]]??-_+-cwzrrQrjnxYJmwqmmLcUjj/1}illI::",;l<}}?})trJmqwwQUnnnnnncXXUJU0UxXYnjjjxJqwCrzj!,,::?wv^
   .uO>                    `    "               .`^",:Il!!ii!i!!I;-)!Lr+???]?]]??-_~]ZwLrLUjXnfjjjjrnuuczUUUYYUUUJUUJUCUYXXXXXYUUQUzXUYXXXYCO0YYXuxrrrrjrrnnjzqqj?cQC{;:<0Jl
    [Z|                    '    ,               .`^,;Il!!!iiii>iiI,l-(L]--??]]]]]?_<~CZLxjXL0XcvxjjjfjfjjjjjjrxnunuuvQvnvvccccccvccXYJQZ0LXnunuvcuxrrrrjrrjunjYqmf-}z0L[ljw{
    "L0^                   '.   "'              .`",Il!!!i!ii>i>i!l;!-Yu--?]][[[[]--+XwJjjjjjrrxzLUC0JUYcnffjjrjrrrrvCxuUQLLL0mm0JYvnxxvczXULJJL0LvrjjrjjjrrunjUqqn}?)YQr\mr^
     |m|                    .   ^`               '",Il!ii!iiiii>>>!I;<)O|-[}[[}[[[]-__nZZZLcjffjcZOUrffffjnXCJYXzunnnUnrrrjznjjjjjxvXC0LJQZwwOLYYUUJCUYurrjrrrrjLqO|]]{/CvZOi
     lLC;                   .   '`               '^,;l!i!!!iii>>>>illl+xv}{)){}}}}[[]?--rZmZ0QzjjxQZZLvjffffffffjrxxvYjjjjxQxjjnzYJO0LZqwOO0JJCCCCJYUCQQXrnrrrjrJwqX_?}[[rJwt
      ?w\                        ^               '^":;l!ii!!iiii>>ilII~1Y\{)({{{{{}{{{}]-_(0mO0ujfjnUZqmOYvnrjjjjffjYzjjjnYcvXYYQZ0mm0LQOJzurjjrrrjjjjrrvUnjrjrrzOqw[?1}}}/0Z>
       f0+                       ^               '`":;l!ii!ii!i>>ii!lI~nwc11)1{{{{{{{{{{}]?+t0wcjfftttz0mmLCQOOLYvxrYYrvzYUYYYQZZwZLJL0Xrjjjrjrjjjrjrrv0YjrrjnzuYOqq/](1}}}jmw>
       "c0l                      '`               `",;!!ii!!iiii>>i!l!1OqJ)1){{{{1{{1{{{}}1{[?\CwZQCnftjC0OmLYYJL00QCZCYczXCLJCQQCLOCcfjjjjrjjrjzUUUOOXrrjjjjrYmOZqqc]fu){{}xwUl
        IJC^                      ^               '":Il!>ii!i!ii>>i!I>QqqY1)1{{11111{11{{{{){n(-)Xw0CufttrXL0wCcczXUJXzzYYXzXQYczQQzjjjjjjjjjjrjrxxxrjrjrrrrrrrYmOqwJ}(j|?-?[\OYi
         ;UmI                     '^              .^,;l!ii!!i!iiiiiil_zqwZv)}{{1111111|(1{{{110\??}JwOcfrrtfvYOZYcccczzccccXJzvYZQrjjjjfjjjjjjjjjjjrjjrjjjjrxxrrQOwqc}(x\~_{{1nqv^
          :UQ~                     `               `,;I!ii!!!iiii>ii_JwQ]:(J{1{11)1)))jX()){}}{J)??+uZCcfU0utjz0mUzzccczvccXcvYOcjjfjfjjjjjjjjrjrjjjrjjrrjrrxxrrY0qqt})u{-{)1{|mL!
           'tm{                     `              `,;;!ii!!!!iiii_x0Y>.  ^fL()(|\\|))r0f())[[]\v]?_Z0cJYrLJJutrCOOOZCYYCm0cvXOzjjjjjjjfjjjjjjjjjrjrjrrjrjjrnxrnY0qm[}ft?]11{}}Xw(
             ]Qu.                    .             '":Ili!i!i!!>1QJ?. .    :mj)(|\|\()|Yr(((1[[(Q\~}ZvncJUjzzcXcvcQwqqwwOCvvz0CrjxzXrjfjjjfjjjjjjjrjrjrjrjrjrrxUUwpn])(]-]}{[]?\ZJ,
              ;vZ}                                 ^,;I!!i!i+|YQjl  '`+};] "Yu1||||\\()nf|(|(}[}Qt>JCnnucXvnnnuvunvwn]|0ZUvzJOYXCYczXnvcxxrjjjrrrrrrrjrrjjrucxYYQqZ)}[?]1mu??-++Yq)
                ~QCl                              .^:;Il>fmwwwwqmOzYZm1 }v'ILC)1|\\\\|)\t||((1]-C/-ZUnnnuccunnxxnucwt<CwZcvXLZ0cXQOZwO\,;vvuzUUCUUYzuxrrjnUrtUJYZqU[Ot-_-QL[++~>}O0l
                 `{Jcl                           ..`,Illi<++>>i><-{Qqx",nU<zQL1?)Yx/\\)(un(|([~]YnCY{uLznuvnnnnnuuJqftmmCvYL00OmZLJni  '/Uj>`  '``^,+fUucX> tmUCqm{{Zn+_+rw\+<<+_/Y_
                   '[Uc<                         ''`";;!i>i!!!!ii>(qL}`_cOmrQZ\?}Xc(\||)\0c{?+<+J],_ .{QJvuunnnnucLwYQwZYXLOwwLut-:    .`   .'       .|0U~  iQUqqx?1On~+~/qj?-]]--_->
                      :/Xx<.                     .^",;l!iiii!i!ii~zwx]l}LZ/{vwc??xY){)([-)m/~<~~un'Y~ ."f0YzzzvvccOqLQmmCmwZv` "'        `_1{`   `"-fvnJ1   ^{LqO))~m/~+~{0z]??]]_+cU;
                         ,_(/1?!^                 `":Il!iii!!!!i!?0O\]]1c\}[{rwf>-u|]]{?_+jU~~~<+nllji:`.ivCu|(tnLqw0mwOv{<.    [L>    `~>      I))()[[1r,  |,|wL(;>wt---]XZ1?--?-~vZ+
                                >[`               `":Il!iii!!iii>/mC1]][[[[{{{YQ+>(r]?[?__)x~~<<>[] L1"u\    `}I;zqmZwU~  '   <Qj!'   '        "]]]]]]][1(~:\{ :/l.(w/-??-(mr?-?--<|w(
                                 1U>            '''";Ilii>i!!!ii+vqv[]]][[}{{}+0t',-1-?]-+{L{~~~>1u x{'._n .+l<|~CqOQqu/X[   !("  ?l ;>       "+?]]]][][[}?])t;},?~uZ(?-?]rQJ(?---~]mc^
                                  /0+          .`^",;lli>>!!!!!>]Omf??]]]}}11}"{OOn+>?1||[_]vY]i>+C^ '..c_"]' _t1mwuCq\^`t<       <(^{      ',~?]]]][]]][}[[()_0X~+LQ[???\Zr~Uu[-_<<um]
                                  'rO~         '`",:;l!i>>i!!!!>/wL]??]][{{1|].  '-YO[]nCOZ00wZ~i+Q; '.'Y~^   !Xzq01Qq\^ _l        /(t     ,+-?]?]]]][][][][[~|wc1UmO)-?]U0_'!CmX?!>]J0!
                                   ,UC;       .'`":;I!i>>>!!!!i~Uwc?]??[}{{(|l         `^^" >Xw\![0, .'.!>    ;Jwwj-Lq|^'i<        "/u     !--_-_?]]]]]]][]]]?{O/'`?wu??1wr'  '?c0mOU/>
                                    _w/       '`^,;;l!>><>i!i!i]Qm(???][}{)|>                "X0]rL  ''''     :zqO_>Lq\"'                  ^,;;I!+[]][[][][]]]}O1   |mCtUZ{
                                    'rOI      '`":;Ili>>>i!i!ii\mL[????[}{)|i                  fZQ_  '.''.   'tqQi.iQq/^`                    '`  <[[[][[][][]]]Q1   ()<!,::"
                                     ~0v     .`^,:Ilii><>i!!!i>xwc?-???[}{))>                        '''.'   }Zm(  !Qq/^`                        _}[][[[[[[][?]L1  "z\    'l
                                     :XZ'    '^",;Ili>>>>i!i!i~Xq\--]]?[}{1{l                        ..''.  l0wr`  !Qqt"'                       '[]][][][][]]]}C1  ;Ct`    <;
                                     ./q]   .`^":Il!i>><>!i!ii?LZ?--]]-?}{{}~                        ''''. "XmJI   :Uqz:'                        :+-]][][[][]])Q[  lQr^    ,[I
                                      1w1  '`^",;I!!i><>i!iii>(OY---[[_~]){?I                        ''''' lUO)    ^cqO>`                         ^i?]?]][]]][\m-  `Qc"`    <(~
                                      }w(..``^,:;l!>>><ii!!!i<rw(___~+~';_-<                         '.'.''-QJl     rqO<`                         'l-]??[[]]]}u0!   z0?`^    ir\^
                                      }w\.'`"":;I!!i><>!!i!i!~cw{<~<<:                              .'''''"jZr`     \wZ-'                          "<--?]]--?1UX    _Ou:`'    "jX}`
                                      {w)``^",;Il!ii>>!!!!!!!_LZ>                                   ''.'.'~Cw]      ?Zw)'                          `;+__?]__?|0}    ^cm}^`'     icCr>
                                      \w?`^",:;I!!i>>!!!!l!l!]mY`                                   .'''',fwL:      >Qqr'                           `l+++~~~-rQ"     >0Cl```      ,)juLQJ1
                                     :z0:^^,:;Il!!iilllll!lli}wv                                   .''.''~wm(       "zpL^                           .`I<<>i!?Lt       _QZ+```      ^|v1"
                                     _0("",,;;ll!i!!lIlIlll!i}qc.                                  '.'''"uqY;        /wml.                          ...`"^`,/0<        iQ0/,``     tZY?
                                     >vI",::;Ill!!lIIIIIIll!!}qQ,                                 .''.''_wm)         -Oqj'                                 IYc'          {COr~,^``  ,ju,
                                     _-`",::;Illl;;;;;;IIl!i!(qwl                                 '.''';OwX:         'twY:                       ..        )Q+             >rZJcczcn|l
                                    ~|^`",::;;I;;:;;;;!>_?->_Xmw~                                ''''',zqQ~           >Om-                      ..        lJn'                 '`'
                                   1('`^",,::;Ii[(jn1]_~!>]cv|JZv                               .''''`\wm{            "Yw[                      ..        x0+
                                 ;u-^`"l~-}jXL0x+` 11Il>xLz<  lJZ            "I!I^              ```'`_mwj`            'cw('                    .'.       +Or'
                             ^]XOOXuuxvL0Qz\l    "uO(tQOj;     jU;    I?uLCmOO0OZZOOmmn-l.     '^'''iOwc^              /qv.                    ...       zQ!
                         "~\UmwLzvnr/1l        !uOwmC/!        \f>'_vZZZOOOmZmmZQ0Jn)+l{XmJ}'  ^``'`YqX;               )qc.                   ...       |m)
                    >/vCZwqZn+`                I]i;.         '_ujjQqwOOOOZmwmmZOmwwqwqZJ|l;jCr,^`'"UqJ!                }qc.                   .'.      ~Zc^
                  -uCLUv)!`                                `[c0YLqm0Cv1<l!+_-?][]-+i!I[nCmwz(rmr"`tqO?                 ?qz.                  ...      `Xm?
                                                           >JvX0wj_<1cJZmZZZOOOOOOZmmOUr[i{Zm0Owu)Zw(                  -qz..                 ..'      tm/'
                                                            "rZ0YuUrO0CUUUUUYUYUYUUYUJC0ZmOm0Jmqqmm\                   ~wz.''                .'.     {qx`
                                                              |OwQU|0LUUYUYUYYYUYYYUYYYUYUU0O(1mwmt                    <qc.''               ....    ;0UI
                                                             "xm0Q/\OCYYYYUYUYUYYUYYYUYYYYYJQCuwmj`                    [qc'`'               ..'.    JQ>
                                                             _OwL0[fmJYUUYUUUUYUUUUUUYUYUYYYJZwZ('                     )qv '                ...    \m1
                                                            ^nmOOU-zOUUYUYUUYUUUUYUUYUYYYUYJZwC?                       xwf                 .'..   ;CU,
                                                            `Zw0m{]mQUUYUYUUUUUYUUUUYUUYYYULqq}                        uL(                 '.     ]Z}
                                                            "qZ0?<LZJYUYUUUYUYUUUYUUYUYYUYUOqw_                        xz[                 ..     vCI
                                                            QqZ{~QZCUYUYUUUUUUUYUUUUYUUUYYUZqm<                       'rZ|                 ..    ,Jv"
                                                          ;JmQ-]OZJYUYUYUYUYUUUUUUYUYUUJJYXZqc"                       `zwt                .'.    ]OL;
                                                        ~zmZZ]-QmCUUYUYYYUUUUYUYUUUUUULLcvYZq/                        !Qm}                ..     ^zQi
                                                      iz0cCO?-mZYXXYJYUYYUYUUUUUYUUJQLXunv0qZ!                        {wO>                        }O(
                                                     ?OOjtw/i0OLYzczUJYUUYYUYUUUCQQUvnnnnJqw|                        'xqY,                        ICL>
                                                    (ZO0z]UwZLJJJccczXUCLLJQQQLJXvnunnxxYwmn"                        ,Cqx`                        `jwz<
                                                   rXi-0wr_Yw0UJLcvczXXzvuvvuuuununxxrnCq0/^                         lQqn                        '`"|mQ]
                                                 'Yu. i/ZmY_-JwO0XuvuvvnnnnnnnnnnxxrruOmc>                           1mqx                       `'  ^]OZ/"
                                                IJ)   .1C0JOn++uZwLzvvvnxxxrrrrrrrrxYwz<                             i0qu'                 .^^.       :uwUi
                                               (w<     'tmCcLwO(I<rwmYvuunxxrrjrjrzZZ-                               :CqX,                `"^^^'       .cqZ]
                                             ;CJ;       `)0QzXQwwLn({tuJCCCLJJCYXO0|"                                ^Yq0~              .^^"""`'         nqO[
                                            (mU^          <JmUvuvzLZmZJcf\|\||(xmC~                                   }mqu`            `^^"^""^'          zqO-
                                          ,zwj              +CZYuuuvvccvzzXYXYmqw[                                     jw0?.         '^"^^^"^^`'           cqO<
                                         'zwj                 lrL0UXcvcvcvczY0mOx"                                     .xOr!         `"^""",""^'           ;Lqz^
                                         Qwf                      I\JwwmwmmwmzLY?                                       ^uQ|:         ^,:;;II;:^            \qq)
                                       ^uq/      ..'..'....         ^^^"",::,]wY,                                        lUU),'      .`";IlIIII,`.          !0pL,                                               
                                      '\wC     .''`'`''''''''....  `"""""",::vqn'                                         iYL_".   '''`'`^,;;;;,^`.         'zqw]
                                      }mw-   .'''''`'`'`'`'''''''..^:,,""",,IXq]                                           )mf^`""`'''''''''``^^`'..         (wq|
                                     ;zqU   .''''`'`''`''`'`'''''''";;;:,"",}ZOl                                           _XYI `;,`'`'`'`'`'`''''..         ~mqt
                                     ~Cq{  ..'''`'```''`'''`'``'`'`"III:,,"ivqf'                                           ~JXI.'`^``'`'`'`''`''''..         :Zqr'                                              
                                     ]QZ;  .''''``'`'`''''`'```````,IlII:,,]mL<                                            [Zz:'`'`'``````'`''`'''.'.        .Oqn^
                                     {OX   .'''''''''''.'.'````````;lllI::;cqr'                                            }mUI`'```````````'`''.'...        .Lqx`                                              
                                     )O]  ..'''''''....  .'``^^`^^:i!lIl;,twL!                                             [mO~'`'`````^`^```''''''..        'Lqt                                               
                                     /Cl  ...'.'''...   .''`^`^^^,i>!llII\wZ?                                              _OZ[`````^`^`^^^``'''''.'.        `Oq(                                               
                                    ^vv'   ...'.'.'''..'''`^^^`^">>ii!!!\mw(                                               !0wf````^^^`^^`^``''''''''.'.     "Oq}                                               
                                    ;Ur     ..'''''''''''`^^^^^;<<i>ii~uwZ).                                               ^Jqv^```^^`^^`^^^`'`''`'''''..    !Zm+                                               
                                    >Q\      .'.''````^`^^^^^"I<>ii>>_CqC+                                                  /pLi``^^^^^^^^^^``'`'''''''''    twQ,
                                    _O)      .''`^",,,,,,""""i<>i>i</mwn;                                                   !Zq(^^`^^^^^^^^^```'````'`'''.   cqz                                                
                                    -0}      .'^",:::::::::l<<i>>i~vwm)'                                                     fqLI`^^"^^"^"^^^```'`'`'`'''''.'Yw|                                                
                                    -O{      .`":;:;:;;;;I>+<>>i<?QqUi                                                       iLq)`^^^""^"^^^^^`````'``'`'''':Jm>                                                
                                    -m(     '`,:;;;;;;;;!~+~<>i<\Zwn:                                                         (wZ<^^^"^"^""","""^^^````'`''.lQZI                                                
                                    -wr    '`":;;;IIIIIi+++<>><jwm('                                                          ^vwm?^^^^^""",,:,:,,,,"^^`''''iQC:
                                    -mU^  .^":;;;IIIll>+_~<<~?zwZ]                                                             ,cqO}"^"",,:::;;;:;:;:,,""^'.iQQ:
                                    <mZ> '^",;;;IIIll>+_+<<<?YqJ>                                                                _Yw/:",:::;;;;II;II;I;I;:"`iQ0:
                                    ;Cq/`^^":;IIIIl!>__+~<<?ZwXI                                                                   )wt,,::;;;IIIlllllllll;;:-O0:
                                    ^vqz,^",;;;;Illi__+~~~[Lwx`                                                                     [Zul,;;Illll!!!lll!lllI;<Qw!
                                     twQ:"",;;IIll!__+~~~?Uqu`                                                                       ]mr;;IIll!!!!!!!!!!illIIzq[
                                     }Zm<",:;IIIl!~_++++]Jwf`                                                                         ILj!;Ill!!iiii!!!!i!lI;]mY`
                                     _0w|,,;IIlll>+_+~~+nwx`                                                                           >Lfill!iiiiiiiiiiiiill~QOI
                                     lJqx;:IIll!i~+++++]mf                                                                              !Lvi!!iiiii>iiii>>i!>-vZ-
                                     ,zwJ<Ill!!!>+_++++nC^                                                                               +OC_iiii>>i>>>>>>>>+{)Ju'
                                     "rwU+ll!!!i+__++++qr                                                                                 _wQ[iii>>>>>>><<<<~{1|Ut
                                      {Zc>l!!i!<__++++{w1                                                                                  >0Z(i>>>><><><~~<~}1)(z\
                                      {mni!!ii>+____++fq?                                                                                   >Lw\>><<<<><<<~~~-[11}xn
                                     ^nq/!!!i>____+__+xq{                                                                                    "Xwf<><<<<<<~~+~+}1)1[)C!
                                     >Lw}!!i>~_______+xq|                                                                                     ,XZ|<<<<<<~~++~+{1()}-?X]
                                    ,nqO_!i><__-_-____(wu                                                                                      ^UO{<<~~<~~++++1((){]<_C(
                                   !UqQ]!!i>~---_-____]rJ-                                                                                      >ZY-~<<~~+++_-1(|){]~lIYc
                                  ^UqO}ll!i~_------__-?|Yj                                                                                       tZ(~<~~~+_+_[)((1}]+>;;UX`
                                   xqO]l!i>_-????---___|t'                                                                                       ,L/<<~~~__-]1)(({[?~>l^ Jn
                                   ,zwf<i>~-]??????-__1Yl                                                                                         xU_<~~+__-{))(){]_~>!: ]Q~
                                    ~ZL]+~_]]?]?]?]?-+{j                                                                                          )m{~<~~__[)11){[-+<>!: vq(
                                    ?OO}+-?]]]]]]]??-_?n                                                                                          fZ{~~~+__-??-?-__~>i!+LqC>
                                   ,cwL[_??][]]]]]??-_~u_                                                                                        }C1+~+~+_-----_-_++>iiUqL<
                                   [mm/+_?][][][]]]??-+~L|                                                                                      }Zj_~~+~+__----____~<>nww>
                                  "JqU?_-]][[[]]]]???-+<tO-                                                                                    >Zc-~~~+~+-------___~>{ww_
                                  l0Z}_-?][[[[]]]]]?--+~]Ox.                                                                                  ,LY]><~~~++--?-----__++zwv
                                  `uZ{__-]][[][]]]?--_+~+xLl                                                                                  /O(>>>~~+~+-?-?----__+?Um_
                                   ~OX?_-][[[[]]]??--_+++{C{                                                                                 IJX~i>><~~++-?--?--____?uL"
                                    (m/_-?[[[[[]]??-___++_zx.                                                                                f01li<><<~~+-?-?-?--___+)X
                                    :Xz__?[[[[]]]??--___++(Jl                                                                               !LY<l>><<<~~_---?--___++_fz
                                     /c?_-][}[]]???----_++[C{                                                                               )mx!l><<><<~__-----__++~]LX
                                     -v]+-][[[[]]??---___+_vYl                                                                             `cZ\l>><<~<~+_-----___+++_Y0:
                                     \X-+-?][[]]]???-------/Z]                                                                             ICQ{i><<<~~~_----_--__++++rq|
                                    ;Xn__-?][]]]]??--------}wx:                                                                            ~0Y_><<~<<~+_------____++~{wc`
                                    [Z\+-?]][]]]]???-------?mQ!                                                                            ~0n_<<<~~~++-------____++~+U0>
                                   ^YO{_-][]][]]]]????-?--?-Yw/                                                                            !Cn?-????--]??----_-__+++<~vw-
                                   +0U?--[][]]]]??]})juvuunjYpOl                                                                           ;Yv{[]]][}{|tjxr/{-__+++~><jm)
                                   /qu__?[[[]]]{tnxt1[?]]??-_1Jc                                                                          +Cr-+_fv]+__?--??])jj]_++~>>{Ot.
                                  :0w\+_?[]]}/zj[???]?[vn}??-_-z)                                                                       Iz0?>~_Xv-___--?-?}j[-]|t?+~~i}Zt'
                                  ]ZO-+_?[)rx)[1([?]???]|X)??_+-U_                                                                     _0xi!i+r0-___+--?-]z/-___]|(_>>\m\
                                 .vqU~~_}rx{[]]}xu]]?]]?]jn[?_+<<Li                                                                   `cX_I!!+Jf+____--?-|J?___+__}j+inw-
                                  jwj<_(t}][]]]?]c1??]?]]|z}-_+>,C(                                                                    {L)ll!+C}+++_+--?-\Y-___+++<+{(ZJ;
                                  ,Y0{{[-?]]]]]]?n(]]?]]]1z}-+_>fJI                                                                    `)t?i!>n\~~+++----1X?__+__?]-<\j;
                                   ,Xw0x[??]]]]?]x([??]?][u|)(jCQI                                                                      ;c0mwqZQc|]_--???]{(jYLLLUfl
                                    ^)XOwmQUzvunxUYxrfttjuJQLX|!                                                                           ,<! .;>~~<i!I:"^.                                                    
                                        "i}\uzYUJJJCUXur\?!^                                                                                                                                                    


"""