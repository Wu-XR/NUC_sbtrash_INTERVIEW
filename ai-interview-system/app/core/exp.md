# llm_exceptions.py 解释文档

## 一、这个文件是干什么的？

一句话：**当 LLM 服务出错时，把错误翻译成前端能看懂的 JSON 返回给用户。**

没有这个文件的话，Ollama 没启动时前端收到的是：
```
500 Internal Server Error
{"detail": "Internal Server Error"}   ← 啥也看不懂
```

有了这个文件，前端收到的是：
```json
{
    "error": "llm_connection_error",
    "message": "无法连接到 Ollama",
    "suggestion": "请检查：1. Ollama是否启动(ollama serve) 2. 网络是否正常"
}
```

## 二、文件里有什么？三样东西

```
llm_exceptions.py
│
├── 第一部分：异常类定义（4个 class）
│   告诉 Python "有哪几种错误"
│
├── 第二部分：异常处理器（4个 async 函数）
│   告诉 FastAPI "遇到每种错误返回什么 JSON"
│
└── 第三部分：注册函数（1个函数）
│   在 main.py 里调一次，把处理器挂到 FastAPI 上
```

## 三、第一部分：异常类定义

### 为什么要自定义异常？

Python 自带的 `Exception` 太笼统，就像去医院说"我不舒服"，医生不知道你哪里有问题。
所以我们给每种错误取个名字：

```python
# 老大（基类）：所有 LLM 错误的总称
class LLMClientError(Exception):
    def __init__(self, message="LLM 服务异常", detail=""):
        self.message = message    # 简短的错误信息
        self.detail = detail      # 详细原因（调试用）

# 小弟1：连不上服务
class LLMConnectionError(LLMClientError): ...

# 小弟2：请求超时
class LLMTimeoutError(LLMClientError): ...

# 小弟3：返回的数据有问题
class LLMResponseError(LLMClientError): ...
```

### 它们的家族关系

```
Exception（Python 自带的祖宗）
  └── LLMClientError（老大，兜底用）
        ├── LLMConnectionError（连不上）
        ├── LLMTimeoutError（超时）
        └── LLMResponseError（返回错误）
```

### 每个异常什么时候会出现？

| 异常类 | 什么时候触发 | 举例 |
|--------|-------------|------|
| LLMConnectionError | 服务连不上 | Ollama 没启动、DeepSeek 断网 |
| LLMTimeoutError | 等太久了 | 本地 7B 模型推理超过 300 秒 |
| LLMResponseError | 服务返回了错误 | 模型名字写错、API Key 无效 |
| LLMClientError | 其他未知错误 | 以上都不是的情况（兜底） |

### message 和 detail 的区别

```python
raise LLMConnectionError(
    message="无法连接到 Ollama",                    # ← 给用户看的（简短）
    detail="请确认已启动：ollama serve，地址：localhost:11434"  # ← 给开发者调试的（详细）
)
```

## 四、第二部分：异常处理器

### 处理器是什么？

处理器就是一个函数，FastAPI 在捕获到异常后自动调用它。
每个处理器做三件事：**记日志 → 选状态码 → 返回 JSON**

```python
async def handle_connection_error(request, exc):
    # 1. 记日志（方便你在服务器上查问题）
    logger.error(f"[LLM连接失败] {request.url.path} | {exc.message}")

    # 2. 选 HTTP 状态码 + 3. 返回 JSON
    return JSONResponse(
        status_code=503,          # 503 = 服务不可用
        content={
            "error": "llm_connection_error",
            "message": exc.message,
            "detail": exc.detail,
            "suggestion": "请检查 Ollama 是否启动"
        }
    )
```

### 四个处理器对应四种错误

| 处理器函数 | 接住哪个异常 | HTTP 状态码 | 含义 |
|-----------|------------|------------|------|
| handle_connection_error | LLMConnectionError | 503 | 服务不可用 |
| handle_timeout_error | LLMTimeoutError | 504 | 网关超时 |
| handle_response_error | LLMResponseError | 502 | 错误网关 |
| handle_general_error | LLMClientError | 500 | 兜底 |

### HTTP 状态码怎么理解？

```
2xx = 成功   （200 OK）
4xx = 你的问题（404 找不到页面）
5xx = 服务器的问题 ← 我们用的都是这类
  500 = 通用服务器错误（兜底）
  502 = 服务器收到了，但返回的内容有问题
  503 = 服务器没开 / 不可用
  504 = 服务器太慢，超时了
```

## 五、第三部分：注册函数

### 为什么需要注册？

定义了处理器，FastAPI 不会自动知道。你得告诉它："遇到这种异常，用这个处理器"。

```python
def register_llm_exception_handlers(app):
    app.add_exception_handler(LLMConnectionError, handle_connection_error)
    app.add_exception_handler(LLMTimeoutError, handle_timeout_error)
    app.add_exception_handler(LLMResponseError, handle_response_error)
    app.add_exception_handler(LLMClientError, handle_general_error)  # 兜底放最后！
```

### 为什么兜底放最后？

FastAPI 从上往下匹配。如果老大（LLMClientError）放第一个，
所有小弟的异常都会被老大先接住，小弟的处理器永远用不上。

```
❌ 错误顺序：
  LLMClientError        ← 第一个注册，所有异常都被它接住了
  LLMConnectionError    ← 永远轮不到
  LLMTimeoutError       ← 永远轮不到

✅ 正确顺序：
  LLMConnectionError    ← 先匹配具体的
  LLMTimeoutError       ← 先匹配具体的
  LLMResponseError      ← 先匹配具体的
  LLMClientError        ← 最后兜底，接住漏网之鱼
```

### 在 main.py 里怎么用？

```python
# main.py 里加两行就行
from app.core.llm_exceptions import register_llm_exception_handlers

app = FastAPI(...)
register_llm_exception_handlers(app)  # ← 这一行搞定
```

## 六、整体工作流程

用一个真实例子走一遍（Ollama 没启动时）：

```
1. 前端请求：POST /api/v1/interview/analyze-camera
                    │
2. 路由调用：       ▼
   await llm_client.vision([img_b64])
                    │
3. llm_client.py 里：
   _call_ollama() 尝试连接 localhost:11434
                    │
4. 连不上！第1次失败 → 重试
             第2次失败 → 重试
             第3次失败 → 不试了
                    │
5. raise LLMConnectionError(         ← llm_client.py 抛出异常
       message="无法连接到 Ollama",
       detail="请确认已启动：ollama serve"
   )
                    │
6. 异常往上冒泡 🫧    ▼
                    │
7. FastAPI 拦截 →   ▼                ← llm_exceptions.py 接住异常
   handle_connection_error() 被触发
                    │
8. 返回给前端：     ▼
   HTTP 503
   {
     "error": "llm_connection_error",
     "message": "无法连接到 Ollama",
     "detail": "请确认已启动：ollama serve",
     "suggestion": "请检查：1. Ollama是否启动 2. 网络是否正常"
   }
```

## 七、文件之间的关系

```
llm_exceptions.py          llm_client.py              main.py
(定义异常 + 处理器)         (import 异常，出错时 raise)   (注册处理器)

class LLMConnectionError   from .llm_exceptions import  from app.core.llm_exceptions
         │                  LLMConnectionError            import register_...
         │                        │                              │
         │                  raise LLMConnectionError()           │
         │                        │                              │
handle_connection_error()  ◄──────┘                              │
         │                                                       │
         └───────────── register(app) ◄──────────────────────────┘
```

## 八、总结

| 问题 | 答案 |
|------|------|
| 异常类定义在哪？ | `llm_exceptions.py`（唯一定义的地方） |
| 谁来 raise？ | `llm_client.py` 里的 `_call_ollama()` 和 `_call_deepseek()` |
| 谁来接住？ | `llm_exceptions.py` 里的处理器函数 |
| 怎么生效？ | `main.py` 调 `register_llm_exception_handlers(app)` |

```ascii

BBBBBBBBBBB@@qzczczcccccC&B@BBBpzLWBBBBBB@BBBBBBBBB%pzzczJa88XzcczzcccQdczccXaB@@BBBBBB@BBB@BB@zccccccoBBBBBBBBBJczzz
B%o%BBBBBB@BBB@8CzccXqBBBBBB&Lp%@BBB@@BB@BBB@BB%kXzccccccccccYzcczcccZ&azccczzcXaBBBBBBBBBBB@@BzczcccLBB@BB@@BBBCcccc
BBBoLZdkqkB@@BBBBB8BBBBBBB#bBBB@BBB@BBBBB@B@&ZzccczzzcccccccccccccczLBY*0mzccczzccq%BdB@BBBB@B%cXcccYB@BBBBBBB@BCczcz
BBBBBB%apbBBBB@BB8BB@B@BW&B@B@BBBBBBBBBBB%bXzcccccczcccczzczXczzcccch8czaWQzcczzcccX80Y%BBBBBBBBZzczoBBB@B@B@BBBCczzz
BBBBBBBBB@B@BBW*%@B@BBBBBBBBBBBBBM&BB@@%OzccczcccccccXZhd0zcccczzczz#8ccCwozcczcczzc0Qcz&@BBBB8CcczdB@BBBBBB@BBBUzccc
BBBBBBBB@BB%pkBB@B@BBBBBB@BB%pp&BBBBB8QczczcXcczccZM8ZXzcczczccczzcc*Bzzdz*YQOzzczccqUcz0@BBB@BJczw@BB@BB@@BBB@8zczzz
BB@WoBBBB%0mBBBBBBBB@BBBBBwJMBBBB@BBOzzcc0dzcccQWBkXczzUzczzzzccczccwB8ZzXdzccczzzcUQzczz8BBBBCczLB@@%B@BB@@B@Bkccccz
BBBBBBBWUY8BBBBB@BBBBBB8UU8@@BBBBBozcczw%YcccqB@hzzcccmzcczzck8Woa#8&QzccUCcccccccZUccccz*BB@*zcOBBBBBB@BBBB%&BYccczz
BBBhQ*QzoBBB@BBBBBB@B8YY8BBBBBBBBLcccz&BYcczWBBJcczzYBUcccccczXQCXccczczzo%0zzzXmUzcccczc*@@BZcwBB%YOBBBB@BBQB#cczccc
BBB#mzC%BBBBB@BBBBBBpz0BBBB@BBB#zzczc*@OccLBBWzccczcMhcccczcYzzczcczzcccqBBBBBmYUUczcczzz&BBWY&B8Ycc0BBB@BB#mBmczcccz
BBpzzd@BBBBBBBB@BB%Uzp@BBBBBBBwcczzzZ@%ccqB@%UzcczcO@wcczzczcz0UzzzczYm%BBBBB8bYccccccccQBB@BBB&oCcX8BBBBBBJM&zczcccc
MCczhBBBB@BBBBBB@MccdBBBBBBB%0zcYqczhBBzqBBBwCzzzzcaBkcczcczzcczYwaW%BBBMhwUczcccccczcczMBBBB@BWUYphMBBBB@pUBkJczcczc
XcckBBBBB@@BBBBBozzm@BBBB@B@mcck&zzcOBBo%BBBUMzccczMB%XczccccccccczzzcccczccczcccccccccmB@BBBBWWB@M%BBBBB*zOB0qUccccc
zzkBBBBBBB@BB@B#zcX%@BBBBBBhcX&&zccczhBBBBBMUBLccczWBBOczczzccccczcccczczczczczcccccccZBBBBBB@BBB@BBBBBB8Yc&Bpcdqzczz
z0BBBBBBBBB@BBMzccaBB@BBBBBLY8Bwcczzzz0@@B@kz%BCczc#BB%CzccccccccccccccczczccczccccczaBBB@BBBBB%ZzccUWBBQcOBB&zcQ&Jcc
JBBBBM&BBBBBBWzzY8@BBBBB@B8zW@akcccczzcc0BBhz&BBmczpBBBBp&XzcczcczcccccccccccczzczcqkO0ccczcC#BBB@@B8Ckbcc#BBBkccz*%L
MBB%Z&BBB@BBBJzpB@BBB@BBBBBqBB0MLczczzcccczLM8BBB%mb%8bwBozccczzccczzccccczzzzczzccJ8YcL8BBBBB@BBBBBB%BkcZBBBBBkcczco
BB*C#BBB@BBBOzMBB@BB%BB@B@BMB@YbBCzcccccccczzccczcczUMBBBBBaYzzzzczcccczcccccczcXk8ZwwzJh8BBBBBWBB8BBBhcX&BBB@B@oXccc
%m0mBB@BBBB8X*B@B@BB#BBBBB@BBBUU%MdUzczcccccczcczQ#BBBB@BBB@BBhCczzzzcccczccczm%BBBMLzzczczaBB%XZ@BBB%UcaBBBBBBBB@pXc
QUzWB@BBBBBobBBBBBB@BdBBBBB8BBwccmhzqkmCYXzULwaoqXYo@BBBBBBBB@BBBBWhqm0Omph&BBBB8mZbMB&LccccXo%0cdBB%JcYk8@B@BBBBBBB8
zC0BB@BBB@Bh%B@BBB@@@o#BB@adBBB*0LZ*LzzzcUXo%waXzcc0ZC*BBBBBBBBBBBBBBBBBBB@BWB@BBZcczcXmWQczccL%#mBBMLzzczcXCLqBB@BBB
UcdBBBBBBBBWBBBBBBB@BBLhB&XoBBBBBBBBBozccJcczw&ohLXYZXcczUObWBBBBBBBBB@BWqO&CcM%B@dzczzczCkczczY%@B@@BWLccczcoB@BB@BB
JcwBBBBBBBBBBBB@B@BBB@BMozYBB@BBBBBBBBMdUz0ULUXzUpMkYcccczzoYzcYW%BBB%#Bd0Od*ck#OoBwzcccczzbccccQBB*JzccczJ&@B@@@BBMC
JzX8BBBBBB@BBB@BBBBBBBBQzc#%@@BBBB@BBBBB%aYzpp0Xzzczccczz*BUcZ&bBB%pO0*@W000&X*MZ0m8zczczczXLcccca@%8czO8BB@BBBoLzccz
zkzmBBBBBBBB@BBBBBBBMYcccwMcz08@B@BBBBB@BBBBB8dk8kmwk8BBW8UZd*BBMO00O0ZB8000#XBB@B%BqYccccccCzzccCBpX#BBpzcczcccpzzcc
cXOcZB@BBBBB@BW#dLccccczw8*&aJzzzpW8B@@@@@@@@BBB@@BB%&h8wQZWB8wcdq00000a#00mh%B&qY0BLczcccccUccczU0LYcX&BBwzcczzchXcc
zcOoXL%B@BBBBB&Lccczccza%qzXhq0hwCXcczY0qbaaahbqOLQh8hUUQWBWJzcccCb0000000Oh0Q0OL0B%XccczcccXccczJYzXYzX&BBB*Jzccz#qc
QzQBBkYhBB@BBBBBB8obphWCbQa*Qz0odJcY0mwwwwqpbhohMQYUczq%BMJzccczzzzOqwOmph#@%&OQoB&bzczcccczczzzzpLoBBBB@%BBBB%kUccp%
Wzz&qzJkkb#@BBB@BBBBMqzzdQQL0dW*bqa&Mhpq0UczccccYmzU0Lzh0ccccczcczcczcQOCMWopb%BBZJQzcccccccXzccLpWBBBBBBBBB@B@@BB#ZJ
U&UUXXch@kwBBBBB@BB@%8XcOQQQLQQ&BBBBpczcccczccczcczczcoUzcczzzLpaC*%BW*hpmZd8B%ZXzJzcczcczzdCcc0%BBBB@BBBBBBB@BBBBBBB
cchwYXbBBbWB8BBBBBBB88azXkQQQQQqB&%BOcczczzccczczccczqUQwmOOZZwpqqmZmwoOmO&BMUczccccczczccp*zX*BbBBBBBBBBB@B@B@BBBBBB
cqUd#J&B@BB%JWBBBocXd&o0XJqQQQQQmBq*%zczczzccccczzczcMUcczXXXXYJJLLLL0QUhB#XccccczcccczczzWMhBBBwC%BBBBBBBBB@BB@BB@B%
QpUBoaBBBB@BLmBBBBBBBBBB*zcLOLQQQQQQaCzXzccczccccccczCQLLmk8MXzzzzzzzzz#8zcccccccczczzzcccLBBBBBWzc*@BBBBBBBBBBBBBBBB
ozoBMWBBBBBB*bBBBBB&ddakMp0XzmY0Q0QOZUQO0zcccccccczczczzcccccccczcccccWozcccczzczcccccczcczz#BBB@%Jzmw*BB@@BBB@BBBBBZ
Mz&B8MB@BBBBB#oBBBBB@BBB%do%&YzJ#kBpUcczczcccccczczcccczczczzczccczzzm#zczzzzzccczccccccccccccJqhhqYzcMYZo&BBBB@BBBBU
oX%BBoBBB@BBB%pL&@BBBB@BBB%ZczcCBqcczczzzcccccccccccccczzccccczCqUczXWcczczcXzccccczzccccczccczczcczzmB#pOLCLZbWBBBOc
oYBBB8%BB@@@BB%YcYmhMW#d0zccccc*hzcczzczczcczzzzccczczcccczcczZ#BB*XwmczzcccXzcccczcccczccczzcczczczOBB@B@BBB@BBB%Qzz
aYBB@BBBBBBBB@BBLzccccccccccczMB0czcczcczcczzzzczzczzzczcczzcccb@BBdqYzccczzcCzccccczcccccczczzcccYM@BBBBBBBBBB@pzczc
wz8B@BB@BB@BBBB@BWYzcccccccYdBBWccczcccUbwb8@azcczccccczcccczcYBBB@B0JcczczcccJccccczzYzcccczccL#%BBBBBBBB@@@8Qcczczc
CQ#BBBB@B@BBBBB@@BBBBBBBB8%BBBBmcccczzczpp8XzzzcccccczczczccccdLcQZ%QdczcccczczmzccczcczzXCdhabkB@BBBBBBB%pXcczcccY*%
zdm@BBBB@BB@B@BBBB@BBBBBBBB@BB%8zcccczzzzzzzccczccccccccccczzadzYzb#QUqcczzzccccX*JzzzcczczzC&BBBB@BBB&%BBBBBBBB@BBBB
zz0kBB@BBBBB@BBBBBBBBBBBB@B%wzcZBZcczczzccccLXzcczccczzzccYpBLzcMoz&Xzz*XcccccccczcXk&BBB@BBBBBhJh%BBBB8CcJp*WWM*pCcc
cczO&BBBBBBBBB@B%#*##*okdWood0XcZBBbUzzczczbBBBMZCLCL0wkMaLzz&hmbc0Qc0BB@oJzczcccccccczzYw*%BBBZM#XXbBBBB*XcczzccccXb
czccOM@BB8BB@BB@BBBB@BB@@Ba&BBB&U&d#BBB%%oQYdYczXcc0zzq0zzccz#ccLJ#zpBBB@BW%*mYcUZk*obOYzccczLW#cXowccZ8BBBCcccccUkLc
cczccJb@BOzQdW@@B@BBBBBMBMpo@BBB@8h&ccX0*#XzzXdU&BWwQOdQQO0zcqccCbzL8bLzczccUd&BBBBBB@B@@&qzczcq0ccJkcccwBB%ZzYqkJCzz
czccccz0&@qccczcoBBBB&d8oMB%MWBBBWX*ccczcz*#UcY%B&00#ZQQQQ0pYaOaZpCzccczczcccczzzzzzz#BBBBBWbccz0zcczbzzcYMBBB@MYcXpz
zccccccczJ#BoUzczZ8M&B#8BBBBBBB*Jp8JccczzczWB%MpWQQdLLQQQLwWmd#CcccccczzzcczcccccccccwBBBBBBzwYzCcczzcJccczaB@@BB&Czh
czcczczcccczXYZpdq0OB@@BBBBBB@BBBB0cczzzcccq@BBBwQqQQLQQ0hYhdzczczcccUaczzccczcczzccc0BBBBBozz*CXccczczUccczWBB@BBBB*
cczcczccczzcczczzcczczpBBBB@BBBBBUcccczccczpBBB8QQQLQmaBBBmzzccccczX&bzcczzzcczczzzccdBBBBBJcccLczcccccczzczcWBBBBB@B
czccccczccczccccccczcz*bBBBBBBBazczzczczccX&BBBBQQQ0&BB#qcczccccccOBMcczccccXJCzzXzcX8BBBBaczcczzccccccccczccQBBB@BBB
zcccccczzccccczczzccXbzhBBBBBMYczczzczcczLBBBBBBhQLoMzzcczczzzczzm@BbzcXCOJzcccczzUUBB@BBhccccczzzczcczcccczccMBBBB@@
zczcczcccccmW0UYJL0wLq%BBB*0czcccczcccYm*BBBB@@B@o0bJzccccccczczUBB&OaQzzczzXLpMBB@BBBB%LcczccczccccczzczUccccq@@BB@B
zczzcccczccX&BBB@B@@@8bQccczccczccccczUXJB@BBBB@B@BBpzccczzzcXOq*BBCkXqOwo%B@BBBB@BBBWQzccczzczczcccccccX#zcccQB@BB@B
cccczccccccczaBBMd0UcczzccccccccczczcUzU&%@BB%QYU0hkXzczXLCJXzcca@BaLpczLh%B@BBBB%kLzcczccczcccczczcczzcZ@mcccQB@BB@B
zzczzcccczcccUoZzzzccccczcczczzzO*aMwzccJ%B@oXzcUczcccXccczzcXwW%BBB0Umcccczczcccccccccccczcccczzccczcc0BdpzccmBBBBBB
czczcczzcczcYW&zzcccccch&0cczOMBBBB#wYzccXMUczq%BBQ0cLzXwWBBBB@BBBBBBUzZXccccccczccczczcczcczczzccccczwBBBBYzcaYWBBBB
ccczLcccccccZXWzcczcczcczzccczzcccccczzXdOzLpwBBBB#zczYo%qXzzczccqB@BBUzcYYcczzccccccccczczcczzzzczczMBBZ&BLcJkzzz*@B
zcz*OcccczcccXWzccczzzzczzcczczzcczX0&BmYaOczccWB@@oJ&Qcccccccczzc*BBB@bzccczzczccczccczzcccczcccczOBBBB0QWXcaBMmBBBB
cckBdzzcczcccw*czcccczzcccccczcLaMBBBbL%BB@BdX#BBBB&CcccccczzcccczzaB@B@%0ccccccccczcccczccczcczcL%BBBMaBBazJBBBB@B@B
zX&@W0XzcczzqhccccczzX#dzczYwWBBBBB#ZM@BBBB@BBBBBBhzczzcczccccczcczcOBB@BBBdXcczzcccccczczcccczw8BBB%aBBB%YJO&BBBBB@B
zX8BBMYJUUCoUccccccczcczQ0dh*M8%B%b%B#*BBBB#q*BBBkccczZhM8BB8Wob0zcczzw%BBBBB%qYcccccczcczczQwB@BBBBBBB@%ULQc8BBBB@B@
zzM@BBB*J0YcccccccczzczzzcczzczJhBBBMh*UzLo&@BBB*cXhBBBBBBBBBBBBBB@&mcccUq&BBBBB@8#kmYzzk8WYL%BBBBBB@BBozk#czWBBB@BBB
zcLBBBB@Bkccccczccczcccccczzq&B@B&BBqLBB%dC%BBB@q&@BBB@BBBBBBBB@BBBB%%*XccccczYUYXXcccY0zzO8BBBB@BBBBhYZBB@&XhBB@@B@B
zccLBBBB@BmccczcccqawJzzZ%BBB@B@BoBmOzbBBB@BB@BBB@BBBBBBBBBBBB8JczcczcccccczczzccccccczZWBMQzXQdkpJzY#BBBBBBB*%BBBBBB


```