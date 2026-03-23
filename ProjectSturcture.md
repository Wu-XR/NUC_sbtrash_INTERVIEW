
# AI 采访系统

## 项目结构

```

ai-interview-system/
│
├── app/                                    # 应用代码
│   ├── __init__.py
│   ├── main.py                            # FastAPI 入口（仅创建app + 挂载路由）
│   ├── config.py                          # 配置管理（pydantic-settings, 读取.env）
│   │
│   ├── routers/                           # 路由层（API 接口定义）
│   │   ├── __init__.py
│   │   ├── interview.py                   # 面试相关接口（开始/提交答案/获取结果）
│   │   ├── knowledge.py                   # 知识库管理接口（上传/查询文档）
│   │   └── health.py                      # 健康检查（供 Docker healthcheck 调用）
│   │
│   ├── services/                          # 服务层（业务逻辑编排）
│   │   ├── __init__.py
│   │   ├── interview_service.py           # 面试流程控制（问题生成→回答收集→评分）
│   │   ├── scoring_service.py             # 评分业务逻辑（调用 scorer + LLM）
│   │   └── knowledge_service.py           # 知识库文档处理 pipeline
│   │
│   ├── core/                              # 核心引擎层（底层能力）
│   │   ├── __init__.py
│   │   ├── rag_engine.py                  # RAG 检索逻辑
│   │   ├── multimodal.py                  # 音视频处理（Whisper + OpenCV）
│   │   ├── scorer.py                      # 评分核心算法
│   │   └── llm_client.py                  # LLM 调用封装（OpenAI/本地模型统一接口）
│   │
│   ├── db/                                # 数据层
│   │   ├── __init__.py
│   │   ├── vector_store.py                # 向量数据库连接（Qdrant/Chroma）
│   │   └── session_store.py               # 面试会话存储（Redis）
│   │
│   ├── schemas/                           # 请求/响应 Pydantic 模型
│   │   ├── __init__.py
│   │   ├── interview.py
│   │   └── knowledge.py
│   │
│   └── models/                            # 数据库 ORM 模型（持久化）
│       ├── __init__.py
│       └── interview.py
│
├── knowledge_base/                        # 本地知识库
│   ├── raw/                               # 原始文档（PDF/TXT/WIKITEXT/XML）
│   └── processed/                         # 向量化后的分块缓存
│
├── scripts/                               # 工具脚本
│   ├── ingest_knowledge.py                # 知识库文档导入
│   └── seed_data.py                       # 初始化测试数据
│
├── tests/                                 # 测试
│   ├── __init__.py
│   ├── test_interview.py
│   ├── test_scoring.py
│   └── test_rag.py
│
├── docker/                                # Docker 构建文件（仅 Dockerfile）
│   ├── app/
│   │   └── Dockerfile                     # FastAPI 应用镜像（多阶段构建）
│   └── nginx/
│       ├── Dockerfile                     # Nginx 反向代理镜像
│       └── nginx.conf                     # Nginx 配置
│
├── docker-compose.yml                     # 📍 根目录！开发环境编排（app+redis+qdrant）
├── docker-compose.prod.yml                # 生产环境覆盖（+nginx+日志+SSL）
├── .dockerignore                          # Docker 构建排除文件
├── .env.example                           # 环境变量模板
├── .gitignore
├── requirements.txt                       # Python 依赖
├── pyproject.toml                         # 项目元数据（可替代 requirements.txt）
└── deploy.sh                              # Linux 一键部署脚本

```