# StreamCap 开发环境指南

## 环境要求

| 依赖 | 版本要求 |
|------|----------|
| Python | >= 3.10 |
| FFmpeg | 最新版 |
| uv (推荐) 或 pip | 最新版 |

## 快速开始

### 1. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg -y
```

### 2. 初始化项目

```bash
# 克隆项目（如果还没有）
git clone https://github.com/ihmily/StreamCap.git
cd StreamCap

# 初始化子模块
git submodule update --init --recursive

# 创建配置文件
cp .env.example .env
```

### 3. 安装 Python 依赖

**方式一：使用 uv（推荐）**

```bash
# 创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装 pip（Flet 内部需要）
uv pip install pip

# 安装本地 streamget 子模块
uv pip install -e ./streamget

# 安装项目依赖
uv pip install -r requirements.txt
```

**方式二：使用 pip**

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -e ./streamget
pip install -r requirements.txt
```

**方式三：使用 Poetry**

```bash
poetry install
```

### 4. 启动应用

**桌面模式**（Windows/macOS）：

```bash
python main.py
```

**Web 模式**（Linux 或任意系统）：

```bash
python main.py --web
```

**自定义 Host/Port**：

```bash
python main.py --web --host 0.0.0.0 --port 8080
```

## 配置说明

编辑 `.env` 文件可修改运行配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `PLATFORM` | 运行模式 (`desktop` / `web`) | `desktop` |
| `HOST` | Web 服务监听地址 | `127.0.0.1` |
| `PORT` | Web 服务端口 | `6006` |
| `VIDEO_API_PORT` | 视频 API 端口 | `6007` |
| `TZ` | 时区 | `Asia/Shanghai` |

## WSL 用户注意

如果在 WSL 中运行，需要将 `HOST` 改为 `0.0.0.0` 才能从 Windows 访问：

```bash
# 修改 .env
HOST=0.0.0.0

# 查看 WSL IP
hostname -I | awk '{print $1}'

# 访问地址：http://<WSL_IP>:6006
```

## 一键启动脚本

```bash
# uv 方式完整启动
git submodule update --init --recursive && \
cp .env.example .env && \
uv venv && source .venv/bin/activate && \
uv pip install pip && \
uv pip install -e ./streamget && \
uv pip install -r requirements.txt && \
python main.py --web
```

## Git 配置

### 配置 upstream（首次设置）

本项目 fork 自 [ihmily/StreamCap](https://github.com/ihmily/StreamCap)，submodule 同样 fork 自 [ihmily/streamget](https://github.com/ihmily/streamget)。

```bash
# 主项目添加 upstream
git remote add upstream https://github.com/ihmily/StreamCap.git

# submodule 添加 upstream
cd streamget
git remote add upstream https://github.com/ihmily/streamget.git
cd ..
```

### 同步 upstream 代码

定期从原仓库同步最新代码：

```bash
# 1. 同步 submodule
cd streamget
git fetch upstream
git merge upstream/main
git push origin main
cd ..

# 2. 同步主项目
git fetch upstream
git merge upstream/main

# 3. 更新主项目对 submodule 的引用
git add streamget
git commit -m "chore: sync submodule with upstream"
git push
```

### 提交代码流程

由于使用了 submodule，提交时需要先提交 submodule，再提交主项目：

```bash
# 1. 提交 submodule（如果有改动）
cd streamget
git add .
git commit -m "your commit message"
git push
cd ..

# 2. 提交主项目
git add .
git commit -m "your commit message"
git push
```

