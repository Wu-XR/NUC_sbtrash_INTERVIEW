# docker/app/Dockerfile

# ==========================================
# Stage 1: Builder (构建依赖)
# ==========================================
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统级编译依赖 (用于 opencv-python-headless, pydantic-settings 等)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装 Python 依赖
COPY requirements.txt .
# 如果有 pyproject.toml 也可以在这里安装
# COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ==========================================
# Stage 2: Runner (生产运行环境)
# ==========================================
FROM python:3.11-slim as runner

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash appuser

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_HOME=/app \
    KNOWLEDGE_BASE_DIR=/app/knowledge_base

# 安装运行时必要的系统库 (FFmpeg 用于音视频处理, OpenCV 依赖)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libjpeg62 \
    libopenjp2-7 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR ${APP_HOME}

# 从 Builder 复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 复制应用代码
# 注意：只复制 app 文件夹和必要的配置文件，不复制 scripts 中的本地部署脚本
COPY app/ ./app/
COPY knowledge_base/ ./knowledge_base/
COPY requirements.txt pyproject.toml ./

# 创建数据目录并授权
RUN mkdir -p ${KNOWLEDGE_BASE_DIR}/raw ${KNOWLEDGE_BASE_DIR}/processed uploads \
    && chown -R appuser:appuser ${APP_HOME}

# 切换用户
USER appuser

EXPOSE 8000

# 健康检查 (调用之前定义的 health router)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ping || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
