
#### **3. `./CONTRIBUTING.md`**

```markdown
# 贡献指南

我们热烈欢迎并感谢所有为 Lex Laboris 项目做出贡献的开发者！

## 行为准则
本项目遵循社区普遍接受的友好和互相尊重的行为准则。请确保您的所有互动都是积极和建设性的。

## 技术栈
- **核心后端**: Python 3.8+ (Flask, SQLAlchemy, Pynput, Watchdog, Pillow, ReportLab)
- **前端界面**: Electron, TypeScript
- **代码风格**: Python (PEP 8), TypeScript (Prettier，可通过 `.prettierrc` 配置)

## 如何贡献
1.  **Fork** 本仓库到您的 GitHub 账户。
2.  **Clone** 您的 fork 到本地: `git clone https://github.com/YourUsername/lex-laboris.git`
3.  **创建** 您的特性分支: `git checkout -b feature/AmazingFeature`
4.  **编码** 实现您的新功能或修复。
5.  **提交** 您的更改: `git commit -m 'feat: Add some AmazingFeature'`
6.  **推送** 到您的分支: `git push origin feature/AmazingFeature`
7.  **打开一个 Pull Request** 到主仓库的 `main` 分支。

## 生产模式打包 (开源分发)

为了让不懂编程的用户也能使用，我们需要将 Python 后端和 Electron 前端打包成一个独立的应用。

### 1. 安装打包工具
```bash
# 安装 PyInstaller 用于打包 Python
pip install pyinstaller

# 在 desktop_ui 目录安装 electron-builder (通常已作为 devDependency 安装)
# cd desktop_ui && yarn install && cd ..