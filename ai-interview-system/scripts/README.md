# Ollama 部署脚本使用说明

本目录下提供两个一键部署脚本，帮助团队成员快速配置 Ollama 环境并下载 `qwen2.5vl:7b` 模型。

---

## 脚本列表

| 文件 | 适用系统 | 功能 |
|------|----------|------|
| `setup_ollama_windows.ps1` | Windows（PowerShell） | 检查 Ollama 安装、配置环境变量、下载模型 |
| `setup_ollama_linux.sh`    | Linux / Arch Linux（Bash） | 检查/安装 Ollama、配置环境变量、启动服务、下载模型 |

---

## Windows 用户使用方法

1. **安装 Ollama**（如果还没装）：前往 https://ollama.com/download 下载并安装 Windows 版本。

2. **以管理员身份打开 PowerShell**：
   - 按 `Win + X`，选择「Windows PowerShell（管理员）」

3. **切换到项目根目录**（注意替换为你的实际路径）：
   ```powershell
   cd C:\path\to\your-project\ai-interview-system
   ```

4. **允许脚本执行**（首次运行需要）：
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

5. **运行脚本**：
   ```powershell
   .\scripts\setup_ollama_windows.ps1
   ```

6. 按照脚本提示操作，支持自定义模型存储路径（直接回车使用默认值 `D:\OllamaModels`）。

---

## Linux / Arch Linux 用户使用方法

1. **切换到项目根目录**：
   ```bash
   cd /path/to/your-project/ai-interview-system
   ```

2. **给脚本添加执行权限**（首次运行）：
   ```bash
   chmod +x scripts/setup_ollama_linux.sh
   ```

3. **运行脚本**：
   ```bash
   bash scripts/setup_ollama_linux.sh
   ```

4. 按照脚本提示操作：
   - **Arch Linux**：脚本会自动检测，并提示使用 `sudo pacman -S ollama` 安装
   - **其他 Linux 发行版**：脚本会使用官方安装脚本 `curl -fsSL https://ollama.com/install.sh | sh`

---

## 脚本会设置哪些环境变量

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `OLLAMA_MODELS` | 模型文件的存储路径 | Windows: `D:\OllamaModels`；Linux: `$HOME/ollama_models` |
| `OLLAMA_HOST` | Ollama 下载源地址（国内镜像加速） | `https://ollama.modelscope.cn` |

> **Windows**：环境变量通过 `[Environment]::SetEnvironmentVariable` 永久写入用户环境变量，同时在当前终端立即生效。
>
> **Linux**：环境变量写入 `~/.bashrc`，新开终端自动加载；当前终端通过 `export` 立即生效。脚本具备幂等性，多次运行不会重复添加。

---

## 模型存储位置

| 系统 | 默认模型路径 |
|------|-------------|
| Windows | `D:\OllamaModels` |
| Linux | `~/ollama_models`（即 `/home/你的用户名/ollama_models`） |

模型文件体积较大，`qwen2.5vl:7b` 约占 **5~6 GB** 磁盘空间，请确保所选路径有足够空间。

---

## 硬件要求

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 硬盘空间 | 10 GB 以上（含模型文件） | 20 GB 以上 |
| 内存（RAM） | 8 GB 以上 | 16 GB 以上 |
| 显卡（GPU） | 可选，无 GPU 时以 CPU 推理（速度较慢） | NVIDIA 显卡，显存 8 GB 以上可大幅提速 |

> **提示**：有 GPU 时 Ollama 会自动使用，无需额外配置。

---

## 验证部署是否成功

脚本执行完毕后，可以用以下命令验证：

```bash
# 查看已下载的模型列表
ollama list

# 启动模型进行对话测试
ollama run qwen2.5vl:7b

# 查看 Ollama API 是否可访问
curl http://localhost:11434/api/tags
```

---

## 常见问题

**Q：Windows 上提示"此系统上禁止运行脚本"**

A：以管理员身份运行 PowerShell，执行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Q：下载模型速度很慢**

A：脚本已配置国内镜像源 `https://ollama.modelscope.cn`，如仍然缓慢，可尝试在网络状态更好的时间段下载。

**Q：Ollama 服务无法启动**

A：Linux 上可手动运行 `ollama serve &` 在后台启动服务；Windows 上可在系统托盘找到 Ollama 图标启动。
