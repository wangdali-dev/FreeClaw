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

### 方式一：Release 下载（推荐给非开发者）

从 GitHub Releases 下载 `OpenClawPortableLauncher.exe`，放在一个固定文件夹中运行（例如 `D:\FreeClaw\`）。

启动器会把运行数据写到 exe 同级目录下的 `data/`，因此不建议频繁移动 exe。


### 方式二：源码运行（开发者）

从仓库下载源码，执行：

```bash
python main.py
```

## 运行流程（首次安装）
<img width="1044" height="698" alt="image" src="https://github.com/user-attachments/assets/9aab98c6-1d8b-4836-8d4c-a0a650bdcd7d" />
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

`OpenClawPortableLauncher.exe` 是源码的打包产物，建议通过 GitHub Releases 分发。

## 免责声明

本项目用于本地部署与学习研究，请遵守 OpenClaw 与 Ollama 的相关许可与使用条款。
