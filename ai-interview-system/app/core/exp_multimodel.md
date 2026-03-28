

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