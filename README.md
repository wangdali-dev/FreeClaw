# OpenClaw 便携版启动器（Ollama）

这是一个面向 Windows 的本地启动器，用于一键部署并运行 OpenClaw + Ollama。本项目会自动下载并校验依赖，然后启动本地 Gateway，适合非技术用户快速上手。

## 功能

- 一键安装并启动 OpenClaw、Ollama、Node.js、Git（便携版）
- 一键拉取模型并自动配置 OpenClaw
- 启动/停止服务、打开控制台
- 支持选择下载镜像与模型源

## 目录结构（运行后）

- `dist\data\config\openclaw.json`：OpenClaw 配置文件
- `dist\data\.openclaw\workspace`：工作区（SOUL/USER/BOOTSTRAP 等文件在这里）
- `dist\data\logs`：启动日志

## 使用方式

### 方式一：直接运行可执行文件
<img width="1044" height="698" alt="image" src="https://github.com/user-attachments/assets/9aab98c6-1d8b-4836-8d4c-a0a650bdcd7d" />


双击 `dist\OpenClawPortableLauncher.exe`，按界面提示完成安装并启动。

### 方式二：Python 运行

在项目根目录执行：

```bash
python main.py
```

## 运行流程（首次安装）

1. 选择模型（或填写自定义模型名）
2. 点击“首次安装并启动”
3. 启动器会自动下载依赖、拉取模型、写入配置并启动服务
4. 点击“打开 OpenClaw 控制台”进入 Web UI

## 开发说明

- 启动器入口：`main.py`
- GUI 使用 Tkinter（标准库）
- 依赖下载与校验都在代码内完成，无需额外脚本

## 版本控制建议

本仓库默认忽略以下目录：

- `dist/`：打包产物与运行时环境
- `data/`：运行时数据与模型
- `build/`、`__pycache__/`

如果需要发布可执行文件，建议通过 GitHub Releases 上传二进制文件。

## 免责声明

本项目用于本地部署与学习研究，请遵守 OpenClaw 与 Ollama 的相关许可与使用条款。
