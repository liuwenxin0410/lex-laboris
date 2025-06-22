# Lex Laboris - 工时壁垒 (Python 最终版)

一个开源的、旨在帮助劳动者合法合规记录加班证据的、禁止商用的个人工具。本项目使用 Python 作为核心后端，Electron 作为跨平台用户界面。

## 核心功能 (v0.5 - Beta)

- **高精度活动追踪**: 记录键盘、鼠标、活动窗口焦点。
- **生产力状态判断**: 自动识别“活跃”与“空闲”状态。
- **智能截屏**: 在活跃状态下定时截屏。
- **本地哈希链**: 所有证据通过哈希链连接，存储在本地 SQLite 数据库中，防篡改。
- **环境快照**: 每次开始追踪时，记录系统环境信息，增强证据可信度。
- **PDF报告生成**: 一键生成结构化的、包含封面、摘要和详细日志的证据报告。
- **可视化界面**: 通过 Electron 实时展示追踪状态和活动日志。

## 运行指南

### 1. 环境准备
- **Node.js**: v16 或更高版本，并附带 npm。
- **Python**: v3.8 或更高版本。
- **Yarn**: 全局安装 Yarn (`npm install -g yarn`)。
- **C/C++ 构建工具**:
    - **Windows**: 安装 [Visual Studio](https://visualstudio.microsoft.com/downloads/) 并勾选 "Desktop development with C++"。
    - **macOS**: 安装 Xcode Command Line Tools (`xcode-select --install`)。
    - **Linux (Debian/Ubuntu)**: `sudo apt-get install build-essential`。

### 2. 一键安装依赖
项目提供了一个便捷的 `setup.py` 脚本来处理所有依赖项的安装。

在项目根目录下，打开终端并运行：

```bash
# Windows
python setup.py install

# macOS / Linux
python3 setup.py install

运行：
# Windows
python setup.py dev

项目结构

lex-laboris-final/
├── core_py/
│   ├── assets/
│   │   └── SourceHanSansSC-Regular.otf  <-- The font file
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── report_generator.py
│   ├── requirements.txt
│   ├── system_info.py
│   ├── tracker.py
│   └── window_monitor.py
├── desktop-ui/
│   ├── src/
│   │   ├── capture.ts
│   │   ├── globals.d.ts
│   │   ├── main.ts
│   │   ├── preload.ts
│   │   └── renderer.ts
│   ├── capture.html
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── webpack.config.js
└── setup.py