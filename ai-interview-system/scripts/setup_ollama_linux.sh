#!/bin/bash
# ============================================================
# Ollama + qwen2.5-vl:7b 一键部署脚本（Linux / Arch Linux）
# 用法：bash scripts/setup_ollama_linux.sh
# ============================================================
set -euo pipefail

# ---- 颜色定义 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}$*${NC}"; }
ok()    { echo -e "${GREEN}✅  $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠️   $*${NC}"; }
err()   { echo -e "${RED}❌  $*${NC}"; }
step()  { echo -e "\n${MAGENTA}========== $* ==========${NC}"; }

# ============================================================
# 欢迎信息
# ============================================================
echo ""
echo -e "${CYAN}  ╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}  ║   Ollama + qwen2.5-vl:7b  一键部署脚本       ║${NC}"
echo -e "${CYAN}  ║   适用平台：Linux（含 Arch Linux）             ║${NC}"
echo -e "${CYAN}  ╚══════════════════════════════════════════════╝${NC}"
echo ""
info "本脚本将完成以下工作："
info "  1. 检查并安装 Ollama"
info "  2. 配置环境变量 OLLAMA_MODELS（模型存储路径）"
info "  3. 配置环境变量 OLLAMA_HOST（国内镜像源）"
info "  4. 创建模型目录"
info "  5. 确保 Ollama 服务正在运行"
info "  6. 下载 qwen2.5-vl:7b 模型（可选）"
echo ""

# ============================================================
# 步骤 1：检查并安装 Ollama
# ============================================================
step "步骤 1/6  检查 Ollama 安装状态"

OLLAMA_INSTALLED=false
if command -v ollama &>/dev/null; then
    OLLAMA_VER=$(ollama --version 2>&1 || true)
    ok "Ollama 已安装：$OLLAMA_VER"
    OLLAMA_INSTALLED=true
else
    warn "未检测到 Ollama，需要安装。"
    echo ""

    IS_ARCH=false
    if [ -f /etc/arch-release ]; then
        IS_ARCH=true
        info "检测到 Arch Linux 系统。"
        info "推荐使用 pacman 安装：sudo pacman -S ollama"
    else
        info "非 Arch Linux 系统，将使用官方安装脚本："
        info "  curl -fsSL https://ollama.com/install.sh | sh"
    fi

    read -p "$(echo -e "${YELLOW}是否自动安装 Ollama？[Y/n] ${NC}")" INSTALL_ANSWER
    INSTALL_ANSWER="${INSTALL_ANSWER:-Y}"

    if [[ "$INSTALL_ANSWER" =~ ^[Yy]$ ]]; then
        if $IS_ARCH; then
            sudo pacman -S --noconfirm ollama
        else
            curl -fsSL https://ollama.com/install.sh | sh
        fi

        if command -v ollama &>/dev/null; then
            ok "Ollama 安装成功！"
            OLLAMA_INSTALLED=true
        else
            err "Ollama 安装失败，请手动安装后重新运行此脚本。"
            exit 1
        fi
    else
        err "已取消安装。请手动安装 Ollama 后重新运行此脚本。"
        exit 1
    fi
fi

# ============================================================
# 步骤 2：配置 OLLAMA_MODELS（模型存储路径）
# ============================================================
step "步骤 2/6  配置 OLLAMA_MODELS（模型存储路径）"

DEFAULT_MODELS_PATH="$HOME/ollama_models"
info "默认模型存储路径：$DEFAULT_MODELS_PATH"
read -p "$(echo -e "${YELLOW}请输入自定义路径（直接按回车使用默认值）：${NC}")" CUSTOM_PATH

if [ -z "${CUSTOM_PATH:-}" ]; then
    MODELS_PATH="$DEFAULT_MODELS_PATH"
else
    MODELS_PATH="$CUSTOM_PATH"
    # 基本路径合法性校验：不允许包含危险字符或路径穿越
    if [[ "$MODELS_PATH" == *".."* ]] || [[ "$MODELS_PATH" =~ [\;\&\|\`\$\<\>] ]]; then
        err "路径包含非法字符，请重新运行脚本并输入合法路径。"
        exit 1
    fi
fi

info "将使用模型存储路径：$MODELS_PATH"

# 写入 ~/.bashrc（先去重再添加）
BASHRC="$HOME/.bashrc"

remove_env_from_bashrc() {
    local var_name="$1"
    if grep -qF "export ${var_name}=" "$BASHRC" 2>/dev/null; then
        # 使用固定字符串匹配，避免 sed 正则特殊字符问题
        grep -vF "export ${var_name}=" "$BASHRC" > "${BASHRC}.tmp" && mv "${BASHRC}.tmp" "$BASHRC"
    fi
}

remove_env_from_bashrc "OLLAMA_MODELS"
echo "export OLLAMA_MODELS=\"${MODELS_PATH}\"" >> "$BASHRC"

# 当前 shell 立即生效
export OLLAMA_MODELS="$MODELS_PATH"
ok "OLLAMA_MODELS 已设置为：$MODELS_PATH"

# ============================================================
# 步骤 3：配置 OLLAMA_HOST（国内镜像加速）
# ============================================================
step "步骤 3/6  配置 OLLAMA_HOST（国内镜像加速）"

OLLAMA_HOST_VAL="https://ollama.modelscope.cn"

remove_env_from_bashrc "OLLAMA_HOST"
echo "export OLLAMA_HOST=\"${OLLAMA_HOST_VAL}\"" >> "$BASHRC"

export OLLAMA_HOST="$OLLAMA_HOST_VAL"
ok "OLLAMA_HOST 已设置为：$OLLAMA_HOST_VAL"

# ============================================================
# 步骤 4：创建模型目录
# ============================================================
step "步骤 4/6  创建模型目录"

mkdir -p "$MODELS_PATH"
ok "模型目录已就绪：$MODELS_PATH"

echo ""
info "--- 当前环境变量验证 ---"
echo -e "${WHITE}  OLLAMA_MODELS = ${OLLAMA_MODELS}${NC}"
echo -e "${WHITE}  OLLAMA_HOST   = ${OLLAMA_HOST}${NC}"

# ============================================================
# 步骤 5：确保 Ollama 服务正在运行
# ============================================================
step "步骤 5/6  确保 Ollama 服务正在运行"

SERVICE_STARTED=false

# 尝试 systemctl --user（不需要 root）
if systemctl --user is-active --quiet ollama 2>/dev/null; then
    ok "Ollama 服务（user）已在运行。"
    SERVICE_STARTED=true
elif systemctl --user enable --now ollama 2>/dev/null; then
    ok "Ollama 服务（user）已启动并设置为开机自启。"
    SERVICE_STARTED=true
# 尝试 sudo systemctl（系统级服务）
elif sudo systemctl is-active --quiet ollama 2>/dev/null; then
    ok "Ollama 服务（system）已在运行。"
    SERVICE_STARTED=true
elif sudo systemctl enable --now ollama 2>/dev/null; then
    ok "Ollama 服务（system）已启动并设置为开机自启。"
    SERVICE_STARTED=true
else
    warn "无法通过 systemctl 启动 Ollama 服务。"
    warn "请手动运行：ollama serve &"
    info "尝试在后台手动启动..."
    if ! pgrep -x ollama &>/dev/null; then
        nohup ollama serve &>/tmp/ollama.log &
        sleep 2
        if pgrep -x ollama &>/dev/null; then
            ok "Ollama 已在后台启动（PID: $(pgrep -x ollama)）"
            SERVICE_STARTED=true
        else
            err "后台启动失败，请手动运行：ollama serve"
        fi
    else
        ok "Ollama 进程已在运行（PID: $(pgrep -x ollama)）"
        SERVICE_STARTED=true
    fi
fi

# ============================================================
# 步骤 6：下载 qwen2.5-vl:7b 模型
# ============================================================
step "步骤 6/6  下载 qwen2.5-vl:7b 模型"

warn "模型大小约 5~6 GB，首次下载需要一定时间，请保持网络畅通。"
read -p "$(echo -e "${YELLOW}是否现在下载 qwen2.5-vl:7b？[Y/n] ${NC}")" PULL_ANSWER
PULL_ANSWER="${PULL_ANSWER:-Y}"

MODEL_PULLED=false
if [[ "$PULL_ANSWER" =~ ^[Yy]$ ]]; then
    info "正在下载 qwen2.5-vl:7b，请耐心等待..."
    if ollama pull qwen2.5-vl:7b; then
        ok "模型下载成功！"
        MODEL_PULLED=true
    else
        err "模型下载失败，请检查网络或手动运行：ollama pull qwen2.5-vl:7b"
    fi
else
    warn "已跳过模型下载。稍后可手动运行：ollama pull qwen2.5-vl:7b"
fi

if $MODEL_PULLED; then
    echo ""
    info "--- 已安装模型列表 ---"
    ollama list
fi

# ============================================================
# 验证清单
# ============================================================
echo ""
echo -e "${MAGENTA}  ╔══════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}  ║              🎉  部署验证清单                  ║${NC}"
echo -e "${MAGENTA}  ╚══════════════════════════════════════════════╝${NC}"
echo ""

print_check() {
    local desc="$1"
    local result="$2"
    if $result; then
        echo -e "  ${GREEN}✅  ${desc}${NC}"
    else
        echo -e "  ${RED}❌  ${desc}${NC}"
    fi
}

# 验证各项
MODELS_SET=false
[ "${OLLAMA_MODELS:-}" = "$MODELS_PATH" ] && MODELS_SET=true

HOST_SET=false
[ "${OLLAMA_HOST:-}" = "$OLLAMA_HOST_VAL" ] && HOST_SET=true

DIR_EXISTS=false
[ -d "$MODELS_PATH" ] && DIR_EXISTS=true

print_check "Ollama 已安装"          $OLLAMA_INSTALLED
print_check "OLLAMA_MODELS 已设置"   $MODELS_SET
print_check "OLLAMA_HOST 已设置"     $HOST_SET
print_check "模型目录已创建"          $DIR_EXISTS
print_check "Ollama 服务已运行"       $SERVICE_STARTED
print_check "qwen2.5-vl:7b 已下载"   $MODEL_PULLED

echo ""
info "💡 环境变量已写入 ~/.bashrc，新开终端自动生效。"
info "   当前终端已通过 export 立即生效。"
info "💡 API 地址：http://localhost:11434"
info "💡 测试命令：ollama run qwen2.5-vl:7b"
echo ""
