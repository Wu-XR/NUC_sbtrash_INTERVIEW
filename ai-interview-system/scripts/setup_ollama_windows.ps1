# ============================================================
# Ollama + qwen2.5-vl:7b 一键部署脚本（Windows PowerShell）
# 用法：以管理员身份打开 PowerShell，执行：
#   .\scripts\setup_ollama_windows.ps1
# ============================================================

$ErrorActionPreference = "Stop"

# ---- 颜色辅助函数 ----
function Write-Info  { param($msg) Write-Host $msg -ForegroundColor Cyan }
function Write-OK    { param($msg) Write-Host $msg -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host $msg -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host $msg -ForegroundColor Red }
function Write-Step  { param($msg) Write-Host "`n========== $msg ==========" -ForegroundColor Magenta }

# ============================================================
# 欢迎信息
# ============================================================
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║   Ollama + qwen2.5-vl:7b  一键部署脚本       ║" -ForegroundColor Cyan
Write-Host "  ║   适用平台：Windows（PowerShell）              ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Info "本脚本将完成以下工作："
Write-Info "  1. 检查 Ollama 是否已安装"
Write-Info "  2. 配置环境变量 OLLAMA_MODELS（模型存储路径）"
Write-Info "  3. 配置环境变量 OLLAMA_HOST（国内镜像源）"
Write-Info "  4. 创建模型目录"
Write-Info "  5. 下载 qwen2.5-vl:7b 模型（可选）"
Write-Host ""

# ============================================================
# 步骤 1：检查 Ollama 是否已安装
# ============================================================
Write-Step "步骤 1/5  检查 Ollama 安装状态"

$ollamaInstalled = $false
try {
    $ver = ollama --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-OK "✅ Ollama 已安装：$ver"
        $ollamaInstalled = $true
    }
} catch {
    # 命令不存在
}

if (-not $ollamaInstalled) {
    Write-Warn "⚠️  未检测到 Ollama，请先安装！"
    Write-Warn "   下载地址：https://ollama.com/download"
    Write-Warn "   安装完成后重新运行此脚本。"
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

# ============================================================
# 步骤 2：配置 OLLAMA_MODELS（模型存储路径）
# ============================================================
Write-Step "步骤 2/5  配置 OLLAMA_MODELS（模型存储路径）"

$defaultModelsPath = "D:\OllamaModels"
Write-Info "默认模型存储路径：$defaultModelsPath"
$customPath = Read-Host "请输入自定义路径（直接按回车使用默认值 $defaultModelsPath）"

if ([string]::IsNullOrWhiteSpace($customPath)) {
    $modelsPath = $defaultModelsPath
} else {
    $modelsPath = $customPath.Trim()
    # 基本路径合法性校验：不允许包含危险字符
    if ($modelsPath -match '[<>"|?*]' -or $modelsPath -match '\.\.') {
        Write-Err "❌ 路径包含非法字符，请重新运行脚本并输入合法路径。"
        exit 1
    }
}

Write-Info "将使用模型存储路径：$modelsPath"

# 永久设置用户环境变量（避免 setx 的 1024 字符限制）
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $modelsPath, "User")
# 当前会话立即生效
$env:OLLAMA_MODELS = $modelsPath
Write-OK "✅ OLLAMA_MODELS 已设置为：$modelsPath"

# ============================================================
# 步骤 3：配置 OLLAMA_HOST（国内镜像加速）
# ============================================================
Write-Step "步骤 3/5  配置 OLLAMA_HOST（国内镜像加速）"

$ollamaHost = "https://ollama.modelscope.cn"
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", $ollamaHost, "User")
$env:OLLAMA_HOST = $ollamaHost
Write-OK "✅ OLLAMA_HOST 已设置为：$ollamaHost"

# ============================================================
# 步骤 4：创建模型目录 & 验证环境变量
# ============================================================
Write-Step "步骤 4/5  创建模型目录并验证环境变量"

if (-not (Test-Path $modelsPath)) {
    New-Item -ItemType Directory -Force -Path $modelsPath | Out-Null
    Write-OK "✅ 目录已创建：$modelsPath"
} else {
    Write-OK "✅ 目录已存在：$modelsPath"
}

Write-Host ""
Write-Info "--- 当前环境变量验证 ---"
$verifiedModels = [Environment]::GetEnvironmentVariable("OLLAMA_MODELS", "User")
$verifiedHost   = [Environment]::GetEnvironmentVariable("OLLAMA_HOST", "User")
Write-Host "  OLLAMA_MODELS = $verifiedModels" -ForegroundColor White
Write-Host "  OLLAMA_HOST   = $verifiedHost"   -ForegroundColor White

if ($verifiedModels -eq $modelsPath -and $verifiedHost -eq $ollamaHost) {
    Write-OK "✅ 环境变量设置成功！"
} else {
    Write-Err "❌ 环境变量验证失败，请手动检查！"
}

# ============================================================
# 步骤 5：下载 qwen2.5-vl:7b 模型
# ============================================================
Write-Step "步骤 5/5  下载 qwen2.5-vl:7b 模型"

Write-Warn "⚠️  模型大小约 5~6 GB，首次下载需要一定时间，请保持网络畅通。"
$pullAnswer = Read-Host "是否现在下载 qwen2.5-vl:7b？（直接按回车默认 yes，输入 no 跳过）"

$doPull = $true
if ($pullAnswer.Trim().ToLower() -eq "no" -or $pullAnswer.Trim().ToLower() -eq "n") {
    $doPull = $false
}

$modelPulled = $false
if ($doPull) {
    Write-Info "正在下载 qwen2.5-vl:7b，请耐心等待..."
    try {
        ollama pull qwen2.5-vl:7b
        if ($LASTEXITCODE -eq 0) {
            Write-OK "✅ 模型下载成功！"
            $modelPulled = $true
        } else {
            Write-Err "❌ 模型下载失败（退出码 $LASTEXITCODE），请检查网络或手动运行：ollama pull qwen2.5-vl:7b"
        }
    } catch {
        Write-Err "❌ 模型下载出错：$_"
    }
} else {
    Write-Warn "⏭️  已跳过模型下载。稍后可手动运行：ollama pull qwen2.5-vl:7b"
}

if ($modelPulled) {
    Write-Host ""
    Write-Info "--- 已安装模型列表 ---"
    ollama list
}

# ============================================================
# 验证清单
# ============================================================
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "  ║              🎉  部署验证清单                  ║" -ForegroundColor Magenta
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

$checks = @(
    @{ Name = "Ollama 已安装";          OK = $ollamaInstalled },
    @{ Name = "OLLAMA_MODELS 已设置";   OK = ($verifiedModels -eq $modelsPath) },
    @{ Name = "OLLAMA_HOST 已设置";     OK = ($verifiedHost -eq $ollamaHost) },
    @{ Name = "模型目录已创建";          OK = (Test-Path $modelsPath) },
    @{ Name = "qwen2.5-vl:7b 已下载";  OK = $modelPulled }
)

foreach ($c in $checks) {
    if ($c.OK) {
        Write-Host "  ✅  $($c.Name)" -ForegroundColor Green
    } else {
        Write-Host "  ❌  $($c.Name)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Info "💡 提示：环境变量对新开的终端窗口立即生效。当前终端已通过 `$env:` 立即生效。"
Write-Info "💡 启动 Ollama 服务：在系统托盘找到 Ollama 图标，或运行 ollama serve"
Write-Info "💡 API 地址：http://localhost:11434"
Write-Host ""
