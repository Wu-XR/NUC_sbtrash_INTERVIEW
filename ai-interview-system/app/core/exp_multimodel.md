

#  `multimodel.py` 使用手册

## 初始化

```python
from app.core.multimodal import AudioTranscriber

transcriber = AudioTranscriber()
```

启动时创建一次，全局复用，**不要每次请求都创建**。

---

## 方法一：`to_text()`

### 一句话

**给文件路径，返回文本。**

### 输入

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `audio_path` | `str` | ✅ | 音频文件路径，支持 wav / mp3 / m4a / webm |
| `prompt` | `str` | ❌ | 提示词，提升专业术语识别率 |

### 输出

`str` — 纯文本字符串

### 用法

```python
# 基本用法
text = transcriber.to_text("uploads/answer.wav")
# text 被赋值成了一个 str：（比如如下这样的话
# text = "我认为 Python 的 GIL 是全局解释器锁它会导致多线程无法真正并行"


# 带提示词
text = transcriber.to_text("uploads/answer.wav", prompt="Java 后端面试")
```


---

## 方法二：`from_bytes()`

### 一句话

**给字节流，返回文本。专为 FastAPI 上传文件设计。**

### 输入

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `audio_bytes` | `bytes` | ✅ | 音频的原始字节数据 |
| `suffix` | `str` | ❌ | 文件后缀，默认 `".wav"`，需与实际格式一致 |
| `prompt` | `str` | ❌ | 同上 |

### 输出

`str` — 纯文本字符串（跟 `to_text` 返回的一样）

### 用法

```python
@router.post("/submit-answer")
async def submit_answer(audio: UploadFile):
    text = transcriber.from_bytes(await audio.read())
    # → "我觉得微服务架构的核心优势是解耦"
    return {"transcription": text}
```

```python
# mp3 格式要指定 suffix
text = transcriber.from_bytes(raw_bytes, suffix=".mp3")
```

---

## 方法三：`to_text_with_detail()`

### 一句话

**给文件路径，返回文本 + 每句话的时间戳。**

### 输入

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `audio_path` | `str` | ✅ | 同 `to_text` |
| `prompt` | `str` | ❌ | 同 `to_text` |

### 输出

`dict`，结构固定如下：

```python
{
    "text": "完整的转录文本",
    "segments": [
        {"start": 0.0,  "end": 3.2,  "text": "第一句话"},
        {"start": 3.2,  "end": 5.1,  "text": "第二句话"},
    ],
    "language": "zh"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | `str` | 完整文本，跟 `to_text()` 返回的一样 |
| `segments[].start` | `float` | 这句话开始的秒数 |
| `segments[].end` | `float` | 这句话结束的秒数 |
| `segments[].text` | `str` | 这句话的文本 |
| `language` | `str` | 语言代码，如 `"zh"` `"en"` |

### 用法

```python
detail = transcriber.to_text_with_detail("answer.wav")

# 取完整文本
print(detail["text"])

# 遍历每段
for seg in detail["segments"]:
    print(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")

# 输出：
# [0.0s - 3.2s] 首先我觉得数据库索引很重要
# [3.2s - 5.1s] 然后在实际项目中
# [5.1s - 8.7s] 我通常会用联合索引
```

---


## 方法三：`to_text_with_detail()`

### 输入

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `audio_path` | `str` | ✅ | 同 `to_text` |
| `prompt` | `str` | ❌ | 同 `to_text` |

### 输出

```python
detail = transcriber.to_text_with_detail("answer.wav")

# detail 被赋值成了一个 dict：
# detail = {
#     "text": "首先我觉得数据库索引很重要然后在实际项目中我通常会用联合索引",
#     "segments": [
#         {"start": 0.0,  "end": 3.2,  "text": "首先我觉得数据库索引很重要"},
#         {"start": 3.2,  "end": 5.1,  "text": "然后在实际项目中"},
#         {"start": 5.1,  "end": 8.7,  "text": "我通常会用联合索引"},
#     ],
#     "language": "zh"
# }

type(detail)             # <class 'dict'>
type(detail["text"])     # <class 'str'>     ← 跟 to_text() 返回的一样
type(detail["segments"]) # <class 'list'>    ← 列表，每个元素是个字典
type(detail["language"]) # <class 'str'>
```

### 怎么取值

```python
# 取完整文本（跟 to_text() 拿到的一样）
detail["text"]
# → "首先我觉得数据库索引很重要然后在实际项目中我通常会用联合索引"

# 取第一段的开始时间
detail["segments"][0]["start"]
# → 0.0

# 取第二段的文本
detail["segments"][1]["text"]
# → "然后在实际项目中"

# 遍历所有段落
for seg in detail["segments"]:
    print(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")
# [0.0s - 3.2s] 首先我觉得数据库索引很重要
# [3.2s - 5.1s] 然后在实际项目中
# [5.1s - 8.7s] 我通常会用联合索引
```

---

## 怎么选

| 你的场景 | 用哪个 |
|----------|--------|
| 拿到文本就行，传给 `llm_client.chat()` | `to_text()` |
| FastAPI 接收用户上传的音频 | `from_bytes()` |
| 需要知道每句话的起止时间 | `to_text_with_detail()` |


```ascii art

                                                                                                                                                                                                       
                                                                                                        kh                                                                                             
                                                                                                   !     0@C Lj                                                                                        
                                             Y@c        tM&O                                     L&&#!    u@*^oZ                                                                                       
                                            p@~       "o&&&&j                                   q&&&&Ml    X@h                                                                                         
                                           aw        ;*&&&&&M]                                .o&&&8&&o     q$i                                                                                        
                                          Wx        ~&&&&M#*#k                                L&&&&&&&&p                      ')QqpdY!                                                                 
                                         mc        >#W##*#*#**m                              t*W&&&&&&&&-                   J@$@$@$$$$@c                                                               
                                        Cn        Ih#**#**#*#**(                            ^o#**##W&&&&p                 z@$@$$$$@$@$$$@L                                                             
                                       +c '#C    "h**hh0un//tjff^                          ,o**#**#*#*MW&u               o@$$$@$@$$$8o@@$$X                                                            
                                      `m ,Bf     m*bv\f0c*#*#*#*p                          Y*#*#*#*#*#*#B&Xp0"         ,&$@Urxh$$$BXrrz@$@a                                                            
                                      1" 0/     Ju/Oo*#*#**#**#**t                        x**#**#**#**#*#*C  Ib/       Y$@Lrrrz@$@Oxrrv%$$h                                                            
                                         ~     +0o#**#*#*#*#*#*#**+                      :o*#*#*#*#*#**#**#_   Ia>    'B$MrrxrU@$%urrxC@$$X                                                            
                                             Ic$$W*#*#**#*#**#**#*q.-Q*@$$$a'           `h#**#**#**#*#**#**pm1   Z_    &$Wrrrxa$$@crxn&$$B:                                                            
                                          ]b/"q**@#*#*#****#**#*#%$$$$$$BMooabdqmwpbao****#*#*#**#**#*#*#*#*t (akoL    u@$WCCM@$@$Ba*@$$@u                  "pMQ<                                      
                                        jQ'  X*#*#***#***#*#*#*#$$$$$$$#*#*#**#*#*#***#*#*#**#*#*#*#**#**#*#d          :8$$@$@Zzcv*$$$@$B,                    [8BBa\                                   
                                      ia;   -#*#**##****#**#**#&$$$$$@**#**********#h\((tn0o*#**#*#*#**#*@WW8&w+        c@$$$@0rrrv&$@$$#                      `kB@BBX                                 
                                      o,Irdw#***#***#***bct(((w#$$$$$#*#*#*#*#*#*#*#*z((((((|Uo*#**#*#*#**#*##!ihY       Y$@$$$$$%ux#$$@d                        *BBBB8/                               
                                       i:  v*##*#*#**oU\((()(xo##$$$$%*#&MW###*##*#*#*aY((()()(va#**#*#*#*#W&&C  :&n      |@$@$@$$@$$@$$@~                        h@BBB@o;      (Ww                    
                                        (pq8@M*#*#*#U(((()(\q#**##&$$$$$$$$$$$$$$$$$$@%M*pr(((((|m*#**&W*M&&&W&qd1 wm      `k$$$@$$$@$$@$BI                       ~%@B@BBBr   IMB&;                    
                                      0L` v***#***ht(()((/m**#%$$$$$$$$$$$$$$$$$$$$$$$$$$$$ML\(((|d*#B$@#*&&&&&o^-O#X        )&$$$@$$$$$@$c                        JBBBB@BB0 nBB@h                     
                                    cq.  l*#*#*#*q(((((rd**M$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ar)|q@$$$B*#*&&&&&U              '(w&@$@$@$$U                        ~%@B@BB@BBBB@Bp                     
                                   *]  .1v*#*#**#t(((Ya**%$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$#*#*%%&&&&1                  `q$$$@x                        ^&B@BB@BB@BBBBh                     
                                  Wt>J*j`b#***#**bLp*#*%$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$B*#W$$$8&&8b                   ^W$@@I                         *BBB@BB@BB@B@8I                    
                                   +>   |#*#*#*#*#*##W$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$@$$$$$$$$$$$$W%$$$$$W&&&#v                  `W$$U    )px^                  QB@BBB@BB@BBBBB[                   
                                        q***#*#**#**B$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$@$$$$$$$$$$$$$$$$$*#**#a,                 ,8$a     #@$B'                 zBB@B@BBBB@B@BBBn                  
                                       :a*#*M$B##*M$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$@$$$$$$$@$$$$$$$$$$W*#*#**c                 c$Y     1@$@0                  ZB@BBBB@B@BBB@B@Bj                 
                                       1#*#*W$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$B#**#**t               i*_     -$$$d                 Z$$@BB@B@BBB@B@BBBBB<                
                                       b***#*B$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$8##*o<                     \B@W~                   M$$$BB@BB@BBBB@B@B@U                
                ",                    !*#*#*#*8$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$8dZ%$$$$$$$$$$$$$$$$$$$$$$$$$$$$%,                  ,b@w+                     0$$$@BB@BB@B@BBBBBB&`               
            <q$@$$$$#t`               {*****#**8$$$$$$$$$$$$$$$$WmW$$$$$$$$$$$$$$$pnfz*$$$@&&8B$$$$$$$$$$$$$$$$$$$$$$%*oahdmQYr{>       /t"                        #$$$$@BB@BBBB@B@B@BBu               
          !#@$@$$@$@$$$p`             u*#M$$$$$$$$$$$$$$$$$$$$$$$kvn@$$$$$$$$$$$$YfCB$$$$$*$$BM*M$$$$$$$$$$$$$$$$$$$&***ozZCnfUCQQx                               )$$$$$@@BBB@B@BBB@B@Bm       _zqw    
         n@$$$$$@$$$@$$$%>            Q#**#$$$$$$$$$$$$$$$$$$q@$$$$B08$$$$$$$$$$CUB$$$$$$Q-f#aaao*$$$$$$$$$$$$$$$$$#hOnnLcX***W&&*<     vLon                     +8$$$$$$BB@BB@BB@BBBB@w   >U%BBBL     
        (@$@MvrU@$@$$@$@$b            d#****#B$$$$$$$$$$$BqX)_\wa8@$$$$$$$$$$$$B@$$$$$@aX---------\$$$$$$$$$$$$@BbvrQo#**#*#*#WMu                              {%$$$$$$$$B@BB@BB@BB@B@BwimBBBB@M!      
       '%@B*xrrx8$$8Lxk@$M     }wwbaam**#*###$$$$$$$$$$U__________{ZB$$$$$$$$$$$$$$$&c-------??????W$$$$$$$$$$@MMb**#*#*#*#*#oj                             >q$$$$$$$$$$$BB@BBB@BB@BBB@BBB@B@Bc        
       f$#nrrruW$$%nrrU@$w      k&&bu/\UmM@$$$$$$$$$$$$$$x]+_+_+____?k$$$$$$$$$$$$Bz---?]}111111111&$$$$$$$$$$$MMM#**#**#**a(                           "|8$$$$$$$$$$$$$@B@BB@BBB@BB@BB@B@BB*"         
       L$@%@%B$$$@0rxv&$h        c&M*#*knX$$$$$$$$@$$$$$$$B]_+_++_+__}B$$$$$$$$$$#{-]C$*(1111{{111c$$$$$$$$$$$$M#MM##*#**#w`                         }#$$$$$$$$$$$$$$$$@BBB@BB@B@BB@BB@BBBBX           
       Z$$$$$$8mo$%0uJ$Z          `q**##$$$$$$$$$$$$$$$$$a[)?+__+!<_1_0$$$$$$$$$&??0$$$wj|11{_[11j$$$$$$$$$$$$BMMMMMM#*#**#*d~                   ;L$$$$$$$$$$$$$$$$$$$$B@BBB@BBBB@BBB@BB@M!            
       U$@$@$Ba$Z@$$@B]             >k*#*%$$$$$$$$$$$$$$$$X|||||1i+|a@$$$$$$$$$$$&%$$$Bj)11)1_}jh$$$$$$$$$$$$$W##M#*ooawow***M#_              ,Q$$$$$$$$$$$$$$$$$$$$$$$BB@B@BB@B@BB@BBBBw              
       >@$$$@$$$$$$@$z               O*#**#*$$$$$$$$$$$$$$M\|\|||_?\o$$$$$$$$$$$$$$$$$$#fffc$$$$$$$$$$$$$$$$$WMMCnvUZhhuoXqJcuZaW+          ($$$$$$$$$$$$$$$$$$$$$$$$$@@BBBB@BBBB@BB@B%(               
        C@$@$$@$@$$$$x             "*M**#**#$$$$$$$$$$$$$$$$&Y\||\|\o$$$$$$$$$$$$$$$$$$@dfffY$$$$$$$$$$$$$$$8MM#M***#*#****#W&&&ML'       t$$$$$$$$$$$$$$$$$$$$$$$$$$$BB@B@BB@B@BB@BBW;                
         w@$$$$$$@$@$$p"          :M&Wp/pc0b%$$$$$$$$$$$$$$$$@ooooM$$$$$$$$$$$$$$$$$$$$$$@W##M$$$$$$$$$$$$$%MMMMMM*#*#*##*#M&&&MQ"       o$$$$$@$@$$$$$$$$$$$$$$$$$$$B@BBBB@BBBB@BBBm     {]           
          C$@$@$@$$$@$@$h`        qU*W&YaZY*&$$$$$@M&$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%MMM#MM*#***#***O_          8$$$$@$$$$$$$$$$$$$$$$$$$$$$BBB@B@BB@B@BB@Bn     '8{           
           -%@$$$$@$$$$$$@*'        >ZoM*#*#*$$$$$M#$$$$$$$$$$$$$8$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$W#MMMM##*aZ]              a$$$$$$$@$$$$$$$$$$$$$$$$$$@B@B@BBB@BBB@BB8~      \@:>o         
              }woWB$@$@$@$$$f             '(Op%$$$#$$$$$$$@%&M&BQ&$$$$$$oJ$$$$$$$$$$Lk$$$$$$$$$$$$$$$$$$$$$$$$MM#*Q:                  *$$$$@$@$$$$$$$$$$$$$$$$$$$$$$$$$$$@@B@BB@o       '%L M{         
                     'z*B$$@$r                  cwp$$$$$$MMMMMMMM@$$$$$$@$$$$$$$$$$$Bh@%8&88&W**#MMMMB$$$$$$$$#*c.                   0$$$@$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$@&        wM Lo          
                         `a@$@1             ]dpdpM$$$$$$$MMMMM#MM#8$$$$$mh$$$$$$$$$@&&88&8&#**#**M#MM$$$$$$$$$&*#*f                 1$$$$$$@$$$$$$$$$$$$$$$$$$$$$$$$$$BBBBBBB@Bo       ($t!B\          
                           ,%$c            Oppdpd$$$$$$$$M#MMMMMM#***#W&&88&B$$@@&8&88&&W**#*#**#MMM$$$$$$$$$$%*#**/                %$$$$$@$$$$$$$$$$$$$$$$$$$$$$@BBBB@B@B@BB%B1      <@U Oc           
                 \:         +@_          ?&&8&kp*$$@$$$$$MMM#MM#M#*#***#**M8&8&888&88&##*#*#*aa*#MM$$$$$$$$@$$B#*#**t              h$$$$$$$$$$$$$$$$$$$$$$$$$$$BBBB@B@BBB@BB@Bk       Mw               
                n@$t        1Q          X&&&&&&d$$$$$$$$$8MMMMMMM#hao**#M#**#*M&&8&W*#*%W**hah**#M$$$M%$$$$$$$B**#*#*n            ?$$$$$$$$$$$$$$$$$$$$$$$$$@BB@B@BBBB@B@BB@BBI      Ct                
                `B$%^                  M&&&&&&hd$$$$$$$$$$MM#MM#MMkhahah&&*#****#*#*h*B&ohahh***#MMMMM$$$$$$$$B*#*#*#*U        >Ob@$$$$$$$$$$$$$$$$$$$$$$$$$$$$@@BB@B@BBBB@B%~                         
                  b$%I               `#&&&8&&hpb$$$$$$$$$$$MMMMMM#khhahaM&ho##*#**#*#%%ahaha**###MM#M&$$$$$$$$8*#**#****hahahahahah*$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$BB@BB@B@B&`                          
                   ^8$J             ^*&&&&&&opdd$$$$&@$$$$$$W#MMMMophhah%*ahhao*#**oo@Mahaha*#**MMMMM$$$$$$$$$M**#**##*#ohahahhahahh&$$$$$$$$$$$$$$$$$$$$$@BBB@BB@B@BBBB@Bq                            
                      .jI           b&&&&&&opppp8$$k#MMMW$$$WMMM#MMdbha&8hhahahhahah#@#ahha**#*##MMM$$$$$$$$$%*#*#*#**#*#ahahahahahao$$$$$$$$$$$$$$$@BBBBBBB@BB@BBBB@B@B&:                             
                    tbY            L&&&&&&MpdpdpdppdhMM*p#MMMMMMMMM#da@MhahahahahahaaB8haho*#**MMMMMMMMM*#$$$#**#*#*##&&WWahahahahaho$$$$$$$$$$$$@BB@B@B@B@BB@BB@B@BBB#,                               
                                  O&&&&&&MpdppdppdppdoMappoMM#MM#MMMWMkhahahahahahaha&@*ah*#*#*MM#MMMM##*#$$**#*#*W&&&&&&&Mhhahhahhaa$$$$$$$$$$$BB@BBBB@BBB@BB@BB@BB@BB@BBB@BBB&c                      
                                 \M&&&&&&ddpdppdpdpdpd*apdpd*MMMMM#MMopkhahahahhahhahh&@&o*#**MMMMM#M*#**#**#*#**M&&&&&&&&&aahahahah*$$$$$$$$$$B@BBB@B@BB@BB@BB@BBB@B@BB@B@BBBBBBB%0                   
                                [ppdpdbbpdpppdpdpk8BBB@B@B@B@Bo#MMMMMM*pkhahhahahahahahoBB%*##MM#MM*#**#**#*#**###&&&&&&&&&WhahahahaM$$$$$$$BBBBB@B@BBB@BB@BB@BB@B@BBB@BBBBB@B@B@B@U                   
                               Iqdppdppdppdpdpd8@&kbddpdpdpdpppdppdb*MMaphhahahahahhahaho#BBMMMM#**#*#*#*#*#*#****#&&&8&&8&&*ahahhah%$$$$BB@B@B@BBBB@B@BB@BB@BBBBBB@BBB@BB*(:                          
                              ipdpdppdppdppdpaBopppppdppdpppdpdppdpdpppdppkhahaM&Woahaha**#*WBBB&*#**#**#*#**#*##*#W&&&&&&&&&ahahaho$$$$$$$BBB@B@B@BBBB@BBB@BB@B@B@%Q!                                 
                             "Zt((Jdpdpdpdppk@opdpddppdppdpdpdpdpppdpdppdpdkW&&&&&&*hhao#**#*##MB@B%#*#*#**#*#**#**#W&&&&&&&&Wahaha8@@@$$$$$@BBBBBB@B@BB@B@BB@B&j"                                     
                            `mt(((Updpppdpdpa@*dpdppdppdppdpppppdpdppdpdppppCM&&&&&&oaa**#*#***#*##%@B&**#*#**#**#*##&&&M##*#*ohahWBBBBBB@$$@@B@B@BB@BB@BBBd<                                          
                           ^wpmczZpdpdpdpppdphbpppdppdpdpdpdpddppdpp\vdpdpdC  z&&&&&&oo*#*#*#*#**#***W@B##**#*#*#*#**#****#**#*ahWB@B@B@BBBB@BBB@B@BB@Bc;                                              
                           CpdppwXnvQppdpdppppdpdppdpdppdpppdppdppdw` l0dp{    Y&&&&Ma&&WWM**#*#*#*#*##@B#*#*#*#***#**##*#*#****%B@BBBB@B@B@BB@BBB*t;                                                  
                  U+      Ldppz(((((((/Qpdpddppdpdv((zpppdpdpdppdpp[        "YZZwW*ah#&&&&&W**#**#*#*#*M@8*#*p\(c*#*#**#*#**#*#*%BBB@B@BBB@BBB/^                                                       
                 vb      nppqf(((()(((((jqdppdppdpZrvqpdpdpppppdpdu       iCZZmhqZmbaM&&&&&##*#*#**#**##B%*#*w((x***#*#**#*#*#*#*B@BB@BB@BBBBBB*I                                                      
                +@{     (pdpX((()((()((((updppdppdppdpdpdpdpdpdpppI     _QZZmdkmZmZZw&&&&&W*#**#*#**#*#%B##*#*kb**#*#**#*#**#***#8BB@BBBB@B@B@B@&l                                                     
                Z%I    IqqXj(((((((((()((/ppdpdpdppdpppdpppdpdpppx    (OZp&W*wZZZZmZh&&&8&##*#**#*#*#*#*#**#*#*#*#*#*#**ao*#*#*#*MB@BZ[+__[xaBBBBW                                                     
               :@W'   `L/((((()(()()(((()\ppdppdppdpdqwpdpdpppdpw,  uZZdh#&&W#wZmZZmM&&&&&#**#*#**#**#**#*#**#*#**#av|(((((|Y*#**#%BB&,        fB@|                                                    
               u$*xq  <((()()(((((((()(((updppdppdZ/((((tOvzpppdu:YZZZmaW&&&okmZZmZqW&&&&M*#**#*#**#*#*#**#*#**#*ou(((()(()((|d#**MBBBr          Xc                                                    
               t@O+x  }()(((((()()((((()xqppQvr|(((()(((((((Jdpp0ZZZmZq*w*&WwZmZmZZp*#*##*#*#*#**#*o**#*#**#*#***x((()((((((((n*#**tpB(                                                                
                      ')((()(()(((()((nYvt(((()((()((()()x00ppdqZm#am*dZmmdwZZZZZZmk*#**#**#*#*#*w((\b**#*#**#*#O((((((()(()((n***#a"                                                                  
                        {((((((()((()((((()()(((((((((((uqpppdpwZdW&&&qZZZmZmZmZmZmo#*#**#*#***am/((|b*#*#*#*#**p()()()(((((()/\||\r1                                                                  
                         ?)()()((()(((()((((((()()(()(\mppdpppdbW#W&dZZmZZZZZZZmZZw#**#*#*#az((((((|d*#***#**#*#*c(((((()()((()((()((_                                                                 
                           -(((()((()(((()(()()(((()(()\Jqpddppqm#*&kZmZZmZmZmZZZmp*#**#**#z((((()((X*#*#*#*#*#*#h\)(()((((()(((()(():                                                                 
                              ,!_}{-i:       >)(()((((((((((|xm*&WaZZmZZmZZmZZmZmZk*#*#*#**u()()((((r***#**#**omUr|(((((()((()()(()~                                                                   
                                               >)((()()((()((((Y&&&&#wZZZmZZmZZZZZh#*#**#*#b\((((()(()((((((((((((()()()((()(({+I                                                                      
                                                 <(((((()((()((L8&&&&&omZZmZZZmZmZJ|(tzQZqqwJ((()((()(()()(()(((()((((tcXC0Zv      l>                                                                  
                                                \#&bz\)(((((|ck&&&&&&&&WqZZmZmZZZm/)()(((((((()(((()(((((((((()()((\Ydw#dbZZx      Xp                                                                  
                                               xcXCZkW&&M#M&&&&&&&&&&&&&&dZZZZmZZZY]((()()(()(((()(((()(()()((((((uZwW&&&WqZt      q#                                                                  
                                               junuunuuUbW&&&&&&&8&&8&&&&&bmZZZmZu  :}(((()(((()((()((()(((()()(fQZbW&&WdZZZ(      Mo x'                                                               
                                               !nununununuXk&&&8&&&&&&&&&&&qmZmZ(      ;?)((()((()(|jxrf|()(((r0ZmmWoq&&dZmZ[     !Bw]%"                                                               
                                                [nununununuuumW&&&&&&&8&&&&WmZOi            `_uvU0ZmZZmZZZZZZZZmZZZZmkW&hmZZ_     n@zaZ                                                                
                                                 ]nunuunuunuunuw&&&&8&&&&8&&pC'              xZZmZZZZmZZmZmZZmZZZmZmmMbZZZmZi     W$[                                                                  
                                                  lxununununununud&&&&&&&&&&Q               iZmZZmZmZZZmZZZmZZmZmZm*a&hbZmZO:    ($8`                                                                  
                                    )               (unununununuunY#&&&&&&&u                OZZZmmmZmZmZZmZZmZZZZZZa&&&*mZZ0'    Q$j                                                                   
                                    cx               `tunununuununuud&&8&W_                (#&&&&&&&&&&&MobqmZmZmZkW&WwZZZmC     1z                                                                    
                                     Co!L(             '|unuununununuw&&b'                 o&&&&&&&&&&&&&&&&&&Wopwoa&&hZmZZv                                                                           
                                      f@J\%u              +fnununununuoJ                  n&&&&&&&&&&&&&8&&&&&&&&&&&obbZZZZI                                                                           
                                       i8&,                   ~|tfrnnr|                   h&&&&8&&8&&8&&&&&8&&&&&8&&&&MdZm0`                                                                           
                                         `                                               ?W&&&&&&&&&&&&&&&&&&&&8&&&&&&&&&hQ                                                                            
                                                                                         a&&8&&&&&&&&&&8&&&&&8&&&&&&&&&&&&o                                                                            
                                                                                        >&&&&&&8&&&&&8&&&&8&&&&&&&&&&&&&&&k                                                                            
                                                                                        LobOXvununuununvXQpo#&&&&&&8&&&&&&0                                                                            
                                                                                        iuunuununununuunuununnuvLbM&&&8&&8u                                                                            
                                                                                         +nnununuunununununuununununQ*&&&&-                                                                            
                                                                                          .funuununununununununununuuuub&*`                                                                            
                                                                                             \nnununuunuununununununununvx                                                                             
                                                                                               Itnuunununununuunuunununn|                                                                              
                                                                                       ;\          >jxnunuununununnnr?                                                                                 
                                                                                        X%}               '";;,'                                                                                       
                                                                                          m@@j1%B0                                                                                                     
                                                                                            ]W@$#1                                                                                                     
                                                                                               !p@n                                                                                                    
                                                                                                                                                                                                       
                                                                                                                                                                                                       


```