# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

StreamCap is a multi-platform live stream recording client built with Flet (Python GUI framework based on Flutter). It supports 40+ streaming platforms including Douyin, Kuaishou, TikTok, Twitch, etc.

## Development Commands

```bash
# Initialize project (first time)
git submodule update --init --recursive
cp .env.example .env

# Install dependencies (using uv - recommended)
uv venv && source .venv/bin/activate
uv pip install pip
uv pip install -e ./streamget
uv pip install -r requirements.txt

# Run application
python main.py              # Desktop mode
python main.py --web        # Web mode (default port 6006)
python main.py --web --host 0.0.0.0 --port 8080  # Custom host/port

# Lint
ruff check .
ruff check --fix .          # Auto-fix issues
```

## Architecture

### Core Components

- **`App` class** (`app/app_manager.py`): Central hub managing all application state. Holds references to ConfigManager, RecordingManager, ProcessManager, and all UI pages.

- **streamget submodule** (`streamget/`): External module handling platform-specific stream URL parsing. Changes to streamget must be committed separately before main project commits.

### Key Modules

| Module | Purpose |
|--------|---------|
| `app/core/recording/` | Recording logic - `RecordingManager` orchestrates recordings, `StreamManager` handles FFmpeg processes |
| `app/core/config/` | Configuration management (YAML/JSON) and i18n |
| `app/core/platforms/` | Platform-specific handlers |
| `app/ui/views/` | Main pages: Home, Recordings, Settings, Storage, About |
| `app/ui/components/` | Reusable UI components (RecordingCard, dialogs, etc.) |
| `app/api/` | FastAPI video streaming service (port 6007) |

### Data Flow

1. User adds stream URL → `RecordingManager` validates and creates `Recording` model
2. `RecordingManager.setup_periodic_live_check()` monitors live status via streamget
3. When live detected → `StreamManager` spawns FFmpeg subprocess for recording
4. `AsyncProcessManager` tracks all running processes for cleanup

### Dual-Mode Operation

- **Desktop mode**: Native window with system tray (Windows/macOS)
- **Web mode**: Browser-based UI with authentication support

The mode is determined by `PLATFORM` env var or `--web` flag. Web mode uses `page.run_task()` for async operations and has responsive layout adjustments.

## Git Workflow

This is a fork. Submodule changes require a two-step commit:

```bash
# 1. Commit submodule first
cd streamget && git add . && git commit -m "msg" && git push && cd ..

# 2. Then commit main project
git add . && git commit -m "msg" && git push
```

## Environment Variables

Key settings in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `PLATFORM` | desktop | Runtime mode (desktop/web) |
| `HOST` | 127.0.0.1 | Web server bind address |
| `PORT` | 6006 | Web UI port |
| `VIDEO_API_PORT` | 6007 | Video streaming API port |

## Internationalization

**All user-facing text must use i18n.** Never hardcode display strings.

Language files in `locales/` (zh_CN.json, en.json). Usage pattern:

```python
class MyComponent:
    def __init__(self, app):
        self.app = app
        self._ = {}
        self.load_language()

    def load_language(self):
        language = self.app.language_manager.language
        for key in ("my_component", "base"):  # Load relevant sections
            self._.update(language.get(key, {}))

    def some_method(self):
        # Use self._.get() with fallback
        text = self._.get("my_key", "默认文本")
```

Add new keys to both `locales/zh_CN.json` and `locales/en.json` under appropriate sections.
