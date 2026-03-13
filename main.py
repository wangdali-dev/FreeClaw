import json
import hashlib
import os
import re
import shutil
import socket
import secrets
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
import zipfile
import tkinter as tk
from tkinter import ttk, messagebox


MODEL_CATALOG = [
    {
        "label": "Nanbeige 4.1（3B）",
        "model": "tomng/nanbeige4.1",
        "size": "约 4.2GB",
        "gpu": "RTX 2060/3060/4060 6-8GB 及以上",
    },
    {
        "label": "Nanbeige 4.1（3B，备选）",
        "model": "fauxpaslife/nanbeige4.1",
        "size": "约 4.2GB",
        "gpu": "RTX 2060/3060/4060 6-8GB 及以上",
    },
    {
        "label": "Qwen3.5（0.8B）",
        "model": "qwen3.5:0.8b",
        "size": "约 1.0GB",
        "gpu": "GTX 1650/1060 4GB 及以上",
    },
    {
        "label": "Qwen3.5（2B）",
        "model": "qwen3.5:2b",
        "size": "约 2.7GB",
        "gpu": "RTX 2060/3050 6GB 及以上",
    },
    {
        "label": "Qwen3.5（4B）",
        "model": "qwen3.5:4b",
        "size": "约 3.4GB",
        "gpu": "RTX 3060/4060 8GB 及以上",
    },
]

DEFAULT_MODELS = [item["label"] for item in MODEL_CATALOG]

GITHUB_MIRROR_CHOICES = [
    ("官方源（不加速）", []),
    ("GitHub 加速（自动轮询）", ["https://ghproxy.com/", "https://gh-proxy.org/", "https://gh.llkk.cc/"]),
    ("GitHub 加速（ghproxy.com）", ["https://ghproxy.com/"]),
    ("GitHub 加速（gh-proxy.org）", ["https://gh-proxy.org/"]),
    ("GitHub 加速（gh.llkk.cc）", ["https://gh.llkk.cc/"]),
]

NODE_SOURCE_CHOICES = [
    ("Node.js 官方源", ["https://nodejs.org/dist/"]),
    (
        "Node.js 国内镜像（自动轮询）",
        [
            "https://mirrors.tuna.tsinghua.edu.cn/nodejs-release/",
            "https://mirrors.ustc.edu.cn/nodejs-release/",
            "https://mirrors.aliyun.com/nodejs-release/",
            "https://mirrors.cloud.tencent.com/nodejs-release/",
            "https://repo.huaweicloud.com/nodejs/",
            "https://nodejs.org/dist/",
        ],
    ),
    ("清华镜像", ["https://mirrors.tuna.tsinghua.edu.cn/nodejs-release/"]),
    ("中科大镜像", ["https://mirrors.ustc.edu.cn/nodejs-release/"]),
    ("阿里云镜像", ["https://mirrors.aliyun.com/nodejs-release/"]),
    ("腾讯云镜像", ["https://mirrors.cloud.tencent.com/nodejs-release/"]),
    ("华为云镜像", ["https://repo.huaweicloud.com/nodejs/"]),
]

NPM_REGISTRY_CHOICES = [
    ("npm 官方源", ""),
    ("npmmirror.com（国内）", "https://registry.npmmirror.com"),
]

OLLAMA_MODEL_SERVER_CHOICES = [
    ("Ollama 官方源", ""),
    ("DaoCloud 镜像", "https://ollama.m.daocloud.io"),
]

if getattr(sys, "frozen", False):
    APP_ROOT = os.path.abspath(os.path.dirname(sys.executable))
else:
    APP_ROOT = os.path.abspath(os.path.dirname(sys.argv[0]))
DATA_DIR = os.path.join(APP_ROOT, "data")
DOWNLOADS_DIR = os.path.join(DATA_DIR, "downloads")
RUNTIME_DIR = os.path.join(DATA_DIR, "runtime")
NODE_DIR = os.path.join(RUNTIME_DIR, "node")
NPM_PREFIX_DIR = os.path.join(RUNTIME_DIR, "npm-global")
OLLAMA_DIR = os.path.join(RUNTIME_DIR, "ollama")
GIT_DIR = os.path.join(RUNTIME_DIR, "git")
MODELS_DIR = os.path.join(DATA_DIR, "models")
CONFIG_DIR = os.path.join(DATA_DIR, "config")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
OPENCLAW_LOG_PATH = os.path.join(LOGS_DIR, "openclaw_startup.log")
OLLAMA_LOG_PATH = os.path.join(LOGS_DIR, "ollama.log")
OPENCLAW_CONFIG_PATH = os.path.join(CONFIG_DIR, "openclaw.json")
OPENCLAW_STATE_DIR = os.path.join(DATA_DIR, "state")
WORKSPACE_DIR = os.path.join(DATA_DIR, ".openclaw", "workspace")
GATEWAY_PORT = 18789


class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OpenClaw 便携版启动器 (Ollama)")
        self.geometry("820x520")
        self.resizable(False, False)
        self.model_var = tk.StringVar(value=DEFAULT_MODELS[0])
        self.custom_var = tk.StringVar(value="")
        self.model_info_var = tk.StringVar(value="")
        self.github_mirror_choice_var = tk.StringVar(value=GITHUB_MIRROR_CHOICES[0][0])
        self.node_source_choice_var = tk.StringVar(value=NODE_SOURCE_CHOICES[0][0])
        self.npm_registry_choice_var = tk.StringVar(value=NPM_REGISTRY_CHOICES[0][0])
        self.ollama_model_server_choice_var = tk.StringVar(value=OLLAMA_MODEL_SERVER_CHOICES[0][0])
        self.status_var = tk.StringVar(value="就绪")
        self.runtime_status_var = tk.StringVar(value="服务状态: 未启动")
        self.gateway_status_var = tk.StringVar(value="Gateway: 未运行")
        self.ollama_status_var = tk.StringVar(value="Ollama: 未运行")
        self.env_status_var = tk.StringVar(value="环境: 待检测")
        self.advanced_toggle_text = tk.StringVar(value="高级选项 ▾")
        self.log_height_normal = 14
        self.log_height_advanced = 9
        self.ollama_process = None
        self.gateway_process = None
        self.pending_open_webui = False
        self.busy = False
        self.advanced_visible = False
        self.buttons = []
        self.openclaw_log_cache = ""
        self.ollama_log_cache = ""
        self.status_check_inflight = False
        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(frame, text="OpenClaw 便携版启动器 (Ollama)", font=("Microsoft YaHei", 16, "bold"))
        title.pack(anchor="w")

        hint = ttk.Label(frame, text="依赖不随包附带，将自动下载并校验后启动。")
        hint.pack(anchor="w", pady=(8, 10))

        status_frame = ttk.LabelFrame(frame, text="运行状态")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(status_frame, textvariable=self.runtime_status_var).pack(anchor="w", padx=8, pady=(4, 0))
        ttk.Label(status_frame, textvariable=self.gateway_status_var).pack(anchor="w", padx=8)
        ttk.Label(status_frame, textvariable=self.ollama_status_var).pack(anchor="w", padx=8)
        ttk.Label(status_frame, textvariable=self.env_status_var).pack(anchor="w", padx=8, pady=(0, 4))

        model_frame = ttk.Frame(frame)
        model_frame.pack(fill=tk.X)

        ttk.Label(model_frame, text="模型选择:").pack(side=tk.LEFT)
        model_combo = ttk.Combobox(model_frame, values=DEFAULT_MODELS, textvariable=self.model_var, width=24, state="readonly")
        model_combo.pack(side=tk.LEFT, padx=(8, 16))
        model_combo.bind("<<ComboboxSelected>>", self.on_model_change)

        ttk.Label(model_frame, text="自定义模型:").pack(side=tk.LEFT)
        model_entry = ttk.Entry(model_frame, textvariable=self.custom_var, width=28)
        model_entry.pack(side=tk.LEFT, padx=(8, 0))
        model_entry.bind("<KeyRelease>", self.on_model_change)

        model_info = ttk.Label(frame, textvariable=self.model_info_var)
        model_info.pack(anchor="w", pady=(8, 0))

        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, pady=(12, 6))
        self.start_btn = ttk.Button(action_frame, text="首次安装并启动", command=self.start_install)
        self.start_btn.pack(side=tk.LEFT)
        self.webui_btn = ttk.Button(action_frame, text="打开 OpenClaw 控制台", command=self.open_webui)
        self.webui_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.start_services_btn = ttk.Button(action_frame, text="启动服务", command=self.start_services)
        self.start_services_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.stop_btn = ttk.Button(action_frame, text="停止服务", command=self.stop_services)
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(action_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=12)

        self.advanced_btn = ttk.Button(frame, textvariable=self.advanced_toggle_text, command=self.toggle_advanced)
        self.advanced_btn.pack(anchor="w", pady=(8, 0))

        self.advanced_frame = ttk.Frame(frame)
        advanced_buttons = ttk.Frame(self.advanced_frame)
        advanced_buttons.pack(fill=tk.X, pady=(6, 6))
        self.detect_btn = ttk.Button(advanced_buttons, text="环境检测", command=self.detect_env)
        self.detect_btn.pack(side=tk.LEFT)
        self.node_btn = ttk.Button(advanced_buttons, text="安装 Node", command=self.install_node_only)
        self.node_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.ollama_btn = ttk.Button(advanced_buttons, text="安装 Ollama", command=self.install_ollama_only)
        self.ollama_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.openclaw_btn = ttk.Button(advanced_buttons, text="安装 OpenClaw", command=self.install_openclaw_only)
        self.openclaw_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.model_btn = ttk.Button(advanced_buttons, text="下载模型", command=self.download_model_only)
        self.model_btn.pack(side=tk.LEFT, padx=(8, 0))

        mirror_frame = ttk.Frame(self.advanced_frame)
        mirror_frame.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(mirror_frame, text="GitHub 下载加速:").pack(side=tk.LEFT)
        mirror_combo = ttk.Combobox(
            mirror_frame,
            values=[label for label, _ in GITHUB_MIRROR_CHOICES],
            textvariable=self.github_mirror_choice_var,
            width=44,
            state="readonly",
        )
        mirror_combo.pack(side=tk.LEFT, padx=(8, 0))
        mirror_hint = ttk.Label(self.advanced_frame, text="只加速 GitHub 资源。加速失败会自动回退官方源。")
        mirror_hint.pack(anchor="w", pady=(6, 0))

        node_frame = ttk.Frame(self.advanced_frame)
        node_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(node_frame, text="Node.js 下载源:").pack(side=tk.LEFT)
        node_combo = ttk.Combobox(
            node_frame,
            values=[label for label, _ in NODE_SOURCE_CHOICES],
            textvariable=self.node_source_choice_var,
            width=44,
            state="readonly",
        )
        node_combo.pack(side=tk.LEFT, padx=(8, 0))

        npm_frame = ttk.Frame(self.advanced_frame)
        npm_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(npm_frame, text="npm 安装源:").pack(side=tk.LEFT)
        npm_combo = ttk.Combobox(
            npm_frame,
            values=[label for label, _ in NPM_REGISTRY_CHOICES],
            textvariable=self.npm_registry_choice_var,
            width=44,
            state="readonly",
        )
        npm_combo.pack(side=tk.LEFT, padx=(8, 0))

        model_source_frame = ttk.Frame(self.advanced_frame)
        model_source_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(model_source_frame, text="Ollama 模型源:").pack(side=tk.LEFT)
        model_source_combo = ttk.Combobox(
            model_source_frame,
            values=[label for label, _ in OLLAMA_MODEL_SERVER_CHOICES],
            textvariable=self.ollama_model_server_choice_var,
            width=44,
            state="readonly",
        )
        model_source_combo.pack(side=tk.LEFT, padx=(8, 0))

        self.buttons = [
            self.detect_btn,
            self.node_btn,
            self.ollama_btn,
            self.openclaw_btn,
            self.model_btn,
            self.start_btn,
            self.start_services_btn,
            self.webui_btn,
            self.stop_btn,
            self.advanced_btn,
        ]

        self.log_notebook = ttk.Notebook(frame)
        self.log_notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        launcher_tab = ttk.Frame(self.log_notebook)
        openclaw_tab = ttk.Frame(self.log_notebook)
        ollama_tab = ttk.Frame(self.log_notebook)
        self.log_notebook.add(launcher_tab, text="启动器")
        self.log_notebook.add(openclaw_tab, text="OpenClaw")
        self.log_notebook.add(ollama_tab, text="Ollama")

        self.log = tk.Text(launcher_tab, height=self.log_height_normal, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.configure(state=tk.DISABLED)

        self.openclaw_log = tk.Text(openclaw_tab, height=self.log_height_normal, wrap=tk.WORD)
        self.openclaw_log.pack(fill=tk.BOTH, expand=True)
        self.openclaw_log.configure(state=tk.DISABLED)

        self.ollama_log = tk.Text(ollama_tab, height=self.log_height_normal, wrap=tk.WORD)
        self.ollama_log.pack(fill=tk.BOTH, expand=True)
        self.ollama_log.configure(state=tk.DISABLED)
        self.on_model_change()
        self._refresh_file_logs()
        self.update_runtime_status()

    def toggle_advanced(self):
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.advanced_frame.pack(fill=tk.X, pady=(8, 0), before=self.log_notebook)
            self.advanced_toggle_text.set("高级选项 ▴")
        else:
            self.advanced_frame.pack_forget()
            self.advanced_toggle_text.set("高级选项 ▾")
        height = self.log_height_advanced if self.advanced_visible else self.log_height_normal
        self.log.configure(height=height)
        self.openclaw_log.configure(height=height)
        self.ollama_log.configure(height=height)

    def update_runtime_status(self):
        if self.busy:
            self.after(2000, self.update_runtime_status)
            return
        if self.status_check_inflight:
            self.after(2000, self.update_runtime_status)
            return
        self.status_check_inflight = True
        thread = threading.Thread(target=self._run_status_check, daemon=True)
        thread.start()

    def _run_status_check(self):
        node_exe, node_source = resolve_node_exe()
        openclaw_cmd, openclaw_source = resolve_openclaw_cmd()
        ollama_exe, ollama_source = resolve_ollama_exe()
        _, git_source = resolve_git_dir()
        gateway_ready = is_http_available(f"http://127.0.0.1:{GATEWAY_PORT}/", timeout=1)
        ollama_ready = is_http_available("http://127.0.0.1:11434/", timeout=1)
        payload = {
            "node_exe": node_exe,
            "node_source": node_source,
            "openclaw_cmd": openclaw_cmd,
            "openclaw_source": openclaw_source,
            "ollama_exe": ollama_exe,
            "ollama_source": ollama_source,
            "git_source": git_source,
            "gateway_ready": gateway_ready,
            "ollama_ready": ollama_ready,
        }
        self.after(0, lambda: self._apply_status_check(payload))

    def _apply_status_check(self, payload):
        self.status_check_inflight = False
        node_exe = payload["node_exe"]
        node_source = payload["node_source"]
        openclaw_cmd = payload["openclaw_cmd"]
        openclaw_source = payload["openclaw_source"]
        ollama_exe = payload["ollama_exe"]
        ollama_source = payload["ollama_source"]
        git_source = payload["git_source"]
        gateway_ready = payload["gateway_ready"]
        ollama_ready = payload["ollama_ready"]
        self.env_status_var.set(
            "环境: "
            f"Node {('已安装（' + node_source + '）') if node_exe else '未安装'} | "
            f"OpenClaw {('已安装（' + openclaw_source + '）') if openclaw_cmd else '未安装'} | "
            f"Ollama {('已安装（' + ollama_source + '）') if ollama_exe else '未安装'} | "
            f"Git {('已安装（' + git_source + '）') if git_source else '未安装'}"
        )
        self.gateway_status_var.set("Gateway: 运行中" if gateway_ready else "Gateway: 未运行")
        self.ollama_status_var.set("Ollama: 运行中" if ollama_ready else "Ollama: 未运行")
        if gateway_ready:
            self.runtime_status_var.set("服务状态: 运行中")
        elif ollama_ready:
            self.runtime_status_var.set("服务状态: 部分运行")
        else:
            self.runtime_status_var.set("服务状态: 未启动")
        if not self.busy:
            self.start_services_btn.config(state=tk.DISABLED if gateway_ready else tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL if (gateway_ready or ollama_ready) else tk.DISABLED)
        self.after(2000, self.update_runtime_status)

    def start_install(self):
        self.run_task("首次安装并启动", self._run_install)

    def _run_install(self):
        model = self.get_selected_model()
        github_mirrors = self.get_github_mirrors()
        node_sources = self.get_node_sources()
        npm_registry = self.get_npm_registry()
        model_server = self.get_ollama_model_server()
        self._log(f"选择模型: {model}")
        self._set_status("准备目录")
        ensure_directories(self._log)
        self._set_status("准备 Node.js")
        node_path = ensure_node(self._log, node_sources)
        self._set_status("准备 OpenClaw")
        openclaw_cmd = ensure_openclaw(self._log, node_path, npm_registry, github_mirrors)
        self._set_status("准备 Ollama")
        ollama_exe = ensure_ollama(self._log, github_mirrors)
        self._set_status("启动 Ollama")
        self.ollama_process = ensure_ollama_running(self._log, ollama_exe)
        self._set_status("拉取模型")
        pull_ollama_model(self._log, ollama_exe, model, model_server)
        self._set_status("配置 OpenClaw")
        configure_openclaw(self._log, model, openclaw_cmd, node_path)
        self._set_status("初始化工作区")
        ensure_workspace_initialized(self._log)
        self._set_status("启动 OpenClaw")
        self.gateway_process = start_openclaw_gateway(self._log, openclaw_cmd, node_path)
        self._set_status("完成")
        self._log("全部完成，可以开始使用 OpenClaw。")
        messagebox.showinfo("完成", "已完成部署并启动 OpenClaw。")

    def start_services(self, open_after=False):
        if open_after:
            self.pending_open_webui = True
        self.run_task("启动服务", self._run_start_services)

    def _run_start_services(self):
        ensure_directories(self._log)
        if is_http_available(f"http://127.0.0.1:{GATEWAY_PORT}/", timeout=2):
            self._log("OpenClaw 已在运行。")
            if self.pending_open_webui:
                self.pending_open_webui = False
                webbrowser.open(f"http://127.0.0.1:{GATEWAY_PORT}/")
            return
        node_exe, _ = resolve_node_exe()
        openclaw_cmd, _ = resolve_openclaw_cmd()
        ollama_exe, _ = resolve_ollama_exe()
        if not node_exe or not openclaw_cmd or not ollama_exe:
            raise RuntimeError("依赖未安装，请先点击“首次安装并启动”。")
        model = self.get_selected_model()
        self._set_status("启动 Ollama")
        self.ollama_process = ensure_ollama_running(self._log, ollama_exe)
        self._set_status("检查模型")
        env = os.environ.copy()
        env["OLLAMA_MODELS"] = MODELS_DIR
        result = run_command(f"\"{ollama_exe}\" list", self._log, env=env, check=False)
        model_exists = model in (result.stdout or "")
        if not model_exists:
            self._set_status("拉取模型")
            pull_ollama_model(self._log, ollama_exe, model, self.get_ollama_model_server())
        self._set_status("配置 OpenClaw")
        configure_openclaw(self._log, model, openclaw_cmd, node_exe)
        self._set_status("初始化工作区")
        ensure_workspace_initialized(self._log)
        self._set_status("启动 OpenClaw")
        self.gateway_process = start_openclaw_gateway(self._log, openclaw_cmd, node_exe)
        if self.pending_open_webui:
            self.pending_open_webui = False
            webbrowser.open(f"http://127.0.0.1:{GATEWAY_PORT}/")

    def detect_env(self):
        self.run_task("环境检测", self._detect_env)

    def _detect_env(self):
        ensure_directories(self._log)
        node_exe, node_source = resolve_node_exe()
        openclaw_cmd, openclaw_source = resolve_openclaw_cmd()
        ollama_exe, ollama_source = resolve_ollama_exe()
        _, git_source = resolve_git_dir()
        self._log("环境检测结果：")
        self._log(f"Node.js: {'已安装（' + node_source + '）' if node_exe else '未安装'}")
        self._log(f"OpenClaw: {'已安装（' + openclaw_source + '）' if openclaw_cmd else '未安装'}")
        self._log(f"Ollama: {'已安装（' + ollama_source + '）' if ollama_exe else '未安装'}")
        self._log(f"Git: {'已安装（' + git_source + '）' if git_source else '未安装'}")
        model = self.get_selected_model()
        if not ollama_exe:
            self._log("模型: 无法检测（Ollama 未安装）")
            return
        env = os.environ.copy()
        env["OLLAMA_MODELS"] = MODELS_DIR
        result = run_command(f"\"{ollama_exe}\" list", self._log, env=env, check=False)
        if result.returncode != 0 or has_ollama_app_error(result):
            self._log("模型: 无法检测（Ollama 未运行）")
            return
        model_exists = model in (result.stdout or "")
        self._log(f"模型 {model}: {'已安装' if model_exists else '未安装'}")

    def install_node_only(self):
        self.run_task("安装 Node", self._install_node_only)

    def _install_node_only(self):
        ensure_directories(self._log)
        self._set_status("准备 Node.js")
        ensure_node(self._log, self.get_node_sources())
        self._log("Node.js 安装完成。")

    def install_ollama_only(self):
        self.run_task("安装 Ollama", self._install_ollama_only)

    def _install_ollama_only(self):
        ensure_directories(self._log)
        self._set_status("准备 Ollama")
        ensure_ollama(self._log, self.get_github_mirrors())
        self._log("Ollama 安装完成。")

    def install_openclaw_only(self):
        self.run_task("安装 OpenClaw", self._install_openclaw_only)

    def _install_openclaw_only(self):
        ensure_directories(self._log)
        self._set_status("准备 Node.js")
        node_path = ensure_node(self._log, self.get_node_sources())
        self._set_status("安装 OpenClaw")
        ensure_openclaw(self._log, node_path, self.get_npm_registry(), self.get_github_mirrors())
        self._log("OpenClaw 安装完成。")

    def download_model_only(self):
        self.run_task("下载模型", self._download_model_only)

    def _download_model_only(self):
        ensure_directories(self._log)
        model = self.get_selected_model()
        self._set_status("准备 Ollama")
        ollama_exe = ensure_ollama(self._log, self.get_github_mirrors())
        self._set_status("启动 Ollama")
        self.ollama_process = ensure_ollama_running(self._log, ollama_exe)
        self._set_status("下载模型")
        pull_ollama_model(self._log, ollama_exe, model, self.get_ollama_model_server())
        self._log("模型下载完成。")

    def run_task(self, title, func):
        if self.busy:
            return
        self.busy = True
        self.set_buttons_state(tk.DISABLED)
        self._set_status(f"{title}中")
        thread = threading.Thread(target=self._run_task, args=(title, func), daemon=True)
        thread.start()

    def _run_task(self, title, func):
        try:
            func()
            if self.status_var.get() != "失败":
                self._set_status(f"{title}完成")
        except Exception as exc:
            self._set_status("失败")
            self._log(f"发生错误: {exc}")
            messagebox.showerror("失败", str(exc))
        finally:
            self.busy = False
            self.set_buttons_state(tk.NORMAL)
            self.update_runtime_status()

    def set_buttons_state(self, state):
        for btn in self.buttons:
            btn.config(state=state)

    def get_selected_model(self):
        custom = self.custom_var.get().strip()
        if custom:
            return custom
        entry = self.get_selected_model_entry()
        if entry:
            return entry["model"]
        return self.model_var.get().strip()

    def get_selected_model_entry(self):
        label = self.model_var.get().strip()
        for item in MODEL_CATALOG:
            if item["label"] == label:
                return item
        return None

    def on_model_change(self, event=None):
        custom = self.custom_var.get().strip()
        if custom:
            self.model_info_var.set(f"模型: {custom} | 大小: 以拉取为准 | 推荐显卡: 以实际模型为准")
            return
        entry = self.get_selected_model_entry()
        if not entry:
            self.model_info_var.set("模型信息: 未知")
            return
        self.model_info_var.set(f"模型: {entry['model']} | 大小: {entry['size']} | 推荐显卡: {entry['gpu']}")

    def get_github_mirrors(self):
        label = self.github_mirror_choice_var.get()
        for name, mirrors in GITHUB_MIRROR_CHOICES:
            if name == label:
                return mirrors
        return []

    def get_node_sources(self):
        label = self.node_source_choice_var.get()
        for name, sources in NODE_SOURCE_CHOICES:
            if name == label:
                return sources
        return ["https://nodejs.org/"]

    def get_npm_registry(self):
        label = self.npm_registry_choice_var.get()
        for name, url in NPM_REGISTRY_CHOICES:
            if name == label:
                return url
        return ""

    def get_ollama_model_server(self):
        label = self.ollama_model_server_choice_var.get()
        for name, url in OLLAMA_MODEL_SERVER_CHOICES:
            if name == label:
                return url
        return ""

    def stop_services(self):
        self.run_task("停止服务", self._run_stop_services)

    def _run_stop_services(self):
        if self.gateway_process:
            terminate_process(self.gateway_process)
            self.gateway_process = None
        if self.ollama_process:
            terminate_process(self.ollama_process)
            self.ollama_process = None
        terminate_process_by_port(GATEWAY_PORT, self._log)
        terminate_process_by_port(11434, self._log)
        self._log("已停止 OpenClaw 与 Ollama。")

    def open_webui(self):
        url = f"http://127.0.0.1:{GATEWAY_PORT}/"
        if not is_http_available(url, timeout=2):
            self._log("OpenClaw 控制台未就绪，尝试启动服务。")
            self.start_services(open_after=True)
            return
        openclaw_cmd, _ = resolve_openclaw_cmd()
        node_exe, _ = resolve_node_exe()
        if openclaw_cmd:
            env = os.environ.copy()
            if node_exe:
                node_dir = os.path.dirname(node_exe)
                env = build_node_env(node_dir)
            env["OPENCLAW_CONFIG_PATH"] = OPENCLAW_CONFIG_PATH
            env["OPENCLAW_HOME"] = DATA_DIR
            env["OPENCLAW_STATE_DIR"] = OPENCLAW_STATE_DIR
            result = run_command(f"\"{openclaw_cmd}\" dashboard", self._log, env=env, check=False)
            if result.returncode == 0:
                self._log("已调用 OpenClaw 控制台启动命令")
                return
        webbrowser.open(url)
        self._log(f"OpenClaw 控制台已打开: {url}")

    def _set_status(self, text):
        self.status_var.set(text)

    def _log(self, text):
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _refresh_file_logs(self):
        self._update_file_log(self.openclaw_log, OPENCLAW_LOG_PATH, "openclaw_log_cache")
        self._update_file_log(self.ollama_log, OLLAMA_LOG_PATH, "ollama_log_cache")
        self.after(1500, self._refresh_file_logs)

    def _update_file_log(self, widget, path, cache_attr):
        lines = read_tail(path, max_lines=400)
        content = "\n".join(lines)
        if getattr(self, cache_attr) == content:
            return
        setattr(self, cache_attr, content)
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        if content:
            widget.insert(tk.END, content + "\n")
        widget.see(tk.END)
        widget.configure(state=tk.DISABLED)


def ensure_directories(log):
    for path in [
        DATA_DIR,
        DOWNLOADS_DIR,
        RUNTIME_DIR,
        NODE_DIR,
        NPM_PREFIX_DIR,
        OLLAMA_DIR,
        GIT_DIR,
        MODELS_DIR,
        CONFIG_DIR,
        LOGS_DIR,
        OPENCLAW_STATE_DIR,
        WORKSPACE_DIR,
    ]:
        os.makedirs(path, exist_ok=True)
    log(f"数据目录: {DATA_DIR}")


def ensure_workspace_initialized(log):
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    log(f"工作区路径: {WORKSPACE_DIR}")
    bootstrap_src = os.path.join(DATA_DIR, ".openclaw", "BOOTSTRAP.md")
    bootstrap_dst = os.path.join(WORKSPACE_DIR, "BOOTSTRAP.md")
    if os.path.exists(bootstrap_src) and not os.path.exists(bootstrap_dst):
        shutil.copyfile(bootstrap_src, bootstrap_dst)
        log("已写入: BOOTSTRAP.md")
    workspace_state_dir = os.path.join(WORKSPACE_DIR, ".openclaw")
    os.makedirs(workspace_state_dir, exist_ok=True)
    state_path = os.path.join(workspace_state_dir, "workspace-state.json")
    state = {}
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f) or {}
        except Exception:
            state = {}
    state.setdefault("version", 1)
    state.setdefault("onboardingCompletedAt", int(time.time()))
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def run_command(cmd, log, env=None, check=True):
    log(f"运行: {cmd}")
    result = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
    if result.stdout:
        log(result.stdout.strip())
    if result.stderr:
        log(result.stderr.strip())
    if check and result.returncode != 0:
        raise RuntimeError(f"命令失败: {cmd}")
    return result


def download_file(url, dest_path, log, resume=False):
    log(f"下载: {url}")
    existing = os.path.getsize(dest_path) if resume and os.path.exists(dest_path) else 0
    headers = {}
    if resume and existing:
        headers["Range"] = f"bytes={existing}-"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as resp:
        status = getattr(resp, "status", 200)
        total = resp.length or 0
        if status == 206 and existing and total:
            total += existing
        if status != 206:
            existing = 0
        mode = "ab" if existing else "wb"
        with open(dest_path, mode) as out:
            downloaded = existing
            last_percent = -1
            while True:
                chunk = resp.read(1024 * 512)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)
                if total:
                    percent = int(downloaded * 100 / total)
                    if percent != last_percent:
                        log(f"下载进度: {percent}%")
                        last_percent = percent
    if total and downloaded != total:
        raise RuntimeError("下载未完成")
    log(f"已保存: {dest_path}")


def download_file_with_retries(url, dest_path, log, attempts=3, resume=False):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            download_file(url, dest_path, log, resume=resume)
            return
        except Exception as exc:
            last_error = exc
            log(f"下载失败，重试 {attempt}/{attempts}: {exc}")
            time.sleep(1)
    raise RuntimeError(f"下载失败: {last_error}")


def download_file_with_fallback(url, dest_path, log, mirrors):
    for mirror in mirrors or []:
        mirror_url = mirror + url
        try:
            log(f"尝试镜像: {mirror}")
            download_file_with_retries(mirror_url, dest_path, log, attempts=2, resume=True)
            return
        except Exception as exc:
            log(f"镜像失败，切换下一个: {exc}")
    download_file_with_retries(url, dest_path, log, attempts=2, resume=True)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_node(log, node_sources):
    node_exe, source = resolve_node_exe()
    if node_exe:
        if source == "系统":
            log("检测到系统 Node.js，直接使用。")
        return node_exe
    last_error = None
    sources = node_sources or ["https://nodejs.org/"]
    for base_url in sources:
        zip_path = None
        shasum_path = None
        try:
            index_url = build_node_index_url(base_url)
            log(f"尝试 Node.js 源: {index_url}")
            zip_url, shasum_url, zip_name = resolve_node_zip_urls(index_url)
            zip_path = os.path.join(DOWNLOADS_DIR, zip_name)
            shasum_path = os.path.join(DOWNLOADS_DIR, "node_SHASUMS256.txt")
            if not os.path.exists(shasum_path):
                download_file_with_retries(shasum_url, shasum_path, log, attempts=2, resume=True)
            expected_hash = parse_shasum(shasum_path, zip_name)
            if not os.path.exists(zip_path) or sha256_file(zip_path) != expected_hash:
                download_file_with_retries(zip_url, zip_path, log, attempts=2, resume=True)
            actual_hash = sha256_file(zip_path)
            if actual_hash != expected_hash:
                raise RuntimeError("Node.js 校验失败")
            extract_zip(zip_path, NODE_DIR)
            node_exe = find_executable(NODE_DIR, "node.exe")
            if not node_exe:
                raise RuntimeError("Node.js 解压失败")
            return node_exe
        except Exception as exc:
            last_error = exc
            log(f"Node.js 源失败，切换下一个: {exc}")
            if zip_path and os.path.exists(zip_path):
                os.remove(zip_path)
            if shasum_path and os.path.exists(shasum_path):
                os.remove(shasum_path)
    raise RuntimeError(f"Node.js 下载失败: {last_error}")


def build_node_index_url(base_url):
    base = base_url
    if not base.endswith("/"):
        base += "/"
    return base + "latest-v22.x/"


def resolve_node_zip_urls(index_url):
    with urllib.request.urlopen(index_url, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    matches = re.findall(r'node-v22\.\d+\.\d+-win-x64\.zip', html)
    if not matches:
        raise RuntimeError("无法解析 Node.js 下载地址")
    zip_name = sorted(matches)[-1]
    zip_url = index_url + zip_name
    shasum_url = index_url + "SHASUMS256.txt"
    return zip_url, shasum_url, zip_name


def parse_shasum(path, filename):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.endswith(" " + filename):
                return line.split()[0]
    raise RuntimeError("无法解析 Node.js 校验值")


def extract_zip(zip_path, target_dir):
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(target_dir)


def find_executable(root, name):
    for base, _, files in os.walk(root):
        if name in files:
            return os.path.join(base, name)
    return None


def resolve_node_exe():
    node_exe = find_executable(NODE_DIR, "node.exe")
    if node_exe:
        return node_exe, "便携"
    system_node = shutil.which("node")
    if system_node:
        return system_node, "系统"
    return None, ""


def resolve_openclaw_cmd():
    openclaw_cmd = os.path.join(NPM_PREFIX_DIR, "openclaw.cmd")
    if os.path.exists(openclaw_cmd):
        return openclaw_cmd, "便携"
    system_cmd = shutil.which("openclaw") or shutil.which("openclaw.cmd")
    if system_cmd:
        return system_cmd, "系统"
    return None, ""


def resolve_ollama_exe():
    ollama_exe = find_executable(OLLAMA_DIR, "ollama.exe")
    if ollama_exe:
        return ollama_exe, "便携"
    system_exe = shutil.which("ollama") or shutil.which("ollama.exe")
    if system_exe:
        return system_exe, "系统"
    return None, ""


def resolve_git_dir():
    git_exe = find_executable(GIT_DIR, "git.exe")
    if git_exe:
        return os.path.dirname(git_exe), "便携"
    system_git = shutil.which("git")
    if system_git:
        return os.path.dirname(system_git), "系统"
    return None, ""


def ensure_git(log, github_mirrors):
    git_dir, source = resolve_git_dir()
    if git_dir:
        if source == "系统":
            log("检测到系统 Git，直接使用。")
        return git_dir
    asset = resolve_git_asset()
    zip_path = os.path.join(DOWNLOADS_DIR, asset["name"])
    sha_path = os.path.join(DOWNLOADS_DIR, asset["sha_name"]) if asset.get("sha_name") else None
    if not os.path.exists(zip_path):
        download_file_with_fallback(asset["url"], zip_path, log, github_mirrors)
    if sha_path and not os.path.exists(sha_path):
        download_file_with_fallback(asset["sha_url"], sha_path, log, github_mirrors)
    if not validate_git_asset(zip_path, asset, log):
        log("Git 校验失败，回退官方源重新下载")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        download_file(asset["url"], zip_path, log)
        if sha_path and not os.path.exists(sha_path):
            download_file(asset["sha_url"], sha_path, log)
        if not validate_git_asset(zip_path, asset, log):
            raise RuntimeError("Git 校验失败")
    extract_zip(zip_path, GIT_DIR)
    git_exe = find_executable(GIT_DIR, "git.exe")
    if not git_exe:
        raise RuntimeError("Git 解压失败")
    return os.path.dirname(git_exe)


def resolve_git_asset():
    api_url = "https://api.github.com/repos/git-for-windows/git/releases/latest"
    with urllib.request.urlopen(api_url) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    zip_asset = None
    sha_asset = None
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if name.endswith("busybox-64-bit.zip") and name.startswith("MinGit-"):
            zip_asset = asset
        if name.endswith("busybox-64-bit.zip.sha256") and name.startswith("MinGit-"):
            sha_asset = asset
    if not zip_asset:
        raise RuntimeError("无法解析 Git 下载地址")
    return {
        "name": zip_asset["name"],
        "url": zip_asset["browser_download_url"],
        "size": zip_asset.get("size", 0),
        "sha_name": sha_asset["name"] if sha_asset else "",
        "sha_url": sha_asset["browser_download_url"] if sha_asset else "",
    }


def parse_sha256_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read().strip().split()
    return content[0] if content else ""


def validate_git_asset(path, asset, log):
    expected_size = asset.get("size") or 0
    if expected_size:
        size = os.path.getsize(path)
        if size != expected_size:
            log(f"Git 文件大小不匹配: {size} != {expected_size}")
            return False
    sha_name = asset.get("sha_name") or ""
    if sha_name:
        sha_path = os.path.join(DOWNLOADS_DIR, sha_name)
        if not os.path.exists(sha_path):
            log("Git 校验文件缺失")
            return False
        expected = parse_sha256_file(sha_path)
        if not expected:
            log("Git 校验值解析失败")
            return False
        if sha256_file(path) != expected:
            log("Git 校验值不匹配")
            return False
        return True
    log("Git 未提供校验文件，跳过校验")
    return True


def ensure_openclaw(log, node_exe, npm_registry, github_mirrors):
    openclaw_cmd, source = resolve_openclaw_cmd()
    if openclaw_cmd:
        if source == "系统":
            log("检测到系统 OpenClaw，直接使用。")
        return openclaw_cmd
    node_dir = os.path.dirname(node_exe)
    npm_cmd = os.path.join(node_dir, "npm.cmd")
    if not os.path.exists(npm_cmd):
        raise RuntimeError("npm 不可用")
    git_dir = ensure_git(log, github_mirrors)
    env = build_node_env(node_dir, npm_registry, extra_paths=[git_dir])
    openclaw_cmd = os.path.join(NPM_PREFIX_DIR, "openclaw.cmd")
    if not os.path.exists(openclaw_cmd):
        run_command(f"\"{npm_cmd}\" install -g openclaw@latest", log, env=env)
    if not os.path.exists(openclaw_cmd):
        raise RuntimeError("OpenClaw 安装失败")
    return openclaw_cmd


def ensure_ollama(log, github_mirrors):
    ollama_exe, source = resolve_ollama_exe()
    if ollama_exe:
        if source == "系统":
            log("检测到系统 Ollama，直接使用。")
        return ollama_exe
    asset = resolve_ollama_asset()
    zip_path = os.path.join(DOWNLOADS_DIR, asset["name"])
    if not os.path.exists(zip_path) or sha256_file(zip_path) != asset["sha256"]:
        download_file_with_fallback(asset["url"], zip_path, log, github_mirrors)
    if not validate_ollama_asset(zip_path, asset, log):
        log("校验失败，回退官方源重新下载")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        download_file(asset["url"], zip_path, log)
        if not validate_ollama_asset(zip_path, asset, log):
            raise RuntimeError("Ollama 校验失败")
    extract_zip(zip_path, OLLAMA_DIR)
    ollama_exe = find_executable(OLLAMA_DIR, "ollama.exe")
    if not ollama_exe:
        raise RuntimeError("Ollama 解压失败")
    return ollama_exe


def resolve_ollama_asset():
    api_url = "https://api.github.com/repos/ollama/ollama/releases/latest"
    with urllib.request.urlopen(api_url) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    for asset in data.get("assets", []):
        if asset.get("name") == "ollama-windows-amd64.zip":
            digest = asset.get("digest") or ""
            sha256 = digest.replace("sha256:", "")
            return {
                "name": asset["name"],
                "url": asset["browser_download_url"],
                "sha256": sha256,
                "size": asset.get("size", 0),
            }
    raise RuntimeError("无法解析 Ollama 下载地址")


def validate_ollama_asset(path, asset, log):
    size = os.path.getsize(path)
    expected_size = asset.get("size") or 0
    if expected_size and size != expected_size:
        log(f"Ollama 文件大小不匹配: {size} != {expected_size}")
        return False
    actual = sha256_file(path)
    if actual != asset["sha256"]:
        log("Ollama 校验值不匹配")
        return False
    return True


def build_node_env(node_dir, npm_registry="", extra_paths=None):
    env = os.environ.copy()
    env["NPM_CONFIG_PREFIX"] = NPM_PREFIX_DIR
    if npm_registry:
        env["NPM_CONFIG_REGISTRY"] = npm_registry
    extra = [p for p in (extra_paths or []) if p]
    env["PATH"] = os.pathsep.join(extra + [node_dir, os.path.join(NPM_PREFIX_DIR, "bin"), env.get("PATH", "")])
    return env


def ensure_ollama_running(log, ollama_exe):
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = MODELS_DIR
    result = run_command(f"\"{ollama_exe}\" list", log, env=env, check=False)
    if result.returncode == 0 and not has_ollama_app_error(result):
        return None
    log("尝试启动 Ollama 服务")
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(OLLAMA_LOG_PATH, "a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            f"\"{ollama_exe}\" serve",
            shell=True,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    time.sleep(4)
    result = run_command(f"\"{ollama_exe}\" list", log, env=env, check=False)
    if result.returncode != 0 or has_ollama_app_error(result):
        raise RuntimeError("Ollama 启动失败")
    return process


def pull_ollama_model(log, ollama_exe, model, model_server):
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = MODELS_DIR
    if model_server:
        env["OLLAMA_MODEL_SERVER"] = model_server
    run_command(f"\"{ollama_exe}\" pull {model}", log, env=env)
 
 
def has_ollama_app_error(result):
    stderr = (result.stderr or "").lower()
    return "could not locate ollama app" in stderr


def configure_openclaw(log, model, openclaw_cmd=None, node_exe=None):
    context_window = get_ollama_context_window(model)
    config = {
        "models": {
            "providers": {
                "ollama": {
                    "baseUrl": "http://127.0.0.1:11434",
                    "apiKey": "ollama-local",
                    "api": "ollama",
                    "models": [
                        {
                            "id": model,
                            "name": model,
                            "reasoning": False,
                            "input": ["text"],
                            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                            "contextWindow": context_window,
                            "maxTokens": context_window * 10,
                        }
                    ],
                }
            }
        },
        "agents": {
            "defaults": {
                "model": {
                    "primary": f"ollama/{model}",
                },
                "workspace": WORKSPACE_DIR,
            },
        },
    }
    with open(OPENCLAW_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    log(f"已写入配置: {OPENCLAW_CONFIG_PATH}")
    if not openclaw_cmd or not node_exe:
        return
    node_dir = os.path.dirname(node_exe)
    env = build_node_env(node_dir)
    env["OPENCLAW_CONFIG_PATH"] = OPENCLAW_CONFIG_PATH
    env["OPENCLAW_HOME"] = DATA_DIR
    env["OPENCLAW_STATE_DIR"] = OPENCLAW_STATE_DIR
    run_command(f"\"{openclaw_cmd}\" config set gateway.mode local", log, env=env, check=False)
    token = ""
    result = run_command(f"\"{openclaw_cmd}\" config get gateway.auth.token", log, env=env, check=False)
    if result.stdout:
        token = result.stdout.strip().strip('"').strip("'")
    if not token or token.lower() in {"null", "none"}:
        token = secrets.token_urlsafe(24)
        run_command(f"\"{openclaw_cmd}\" config set gateway.auth.token {token}", log, env=env, check=False)
    run_command(f"\"{openclaw_cmd}\" config set gateway.remote.token {token}", log, env=env, check=False)


def get_ollama_context_window(model):
    try:
        payload = json.dumps({"name": model}).encode("utf-8")
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/show",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        model_info = data.get("model_info", {})
        for key, value in model_info.items():
            if key.endswith(".context_length") and isinstance(value, int):
                return value
    except Exception:
        return 8192
    return 8192


def start_openclaw_gateway(log, openclaw_cmd, node_exe):
    node_dir = os.path.dirname(node_exe)
    env = build_node_env(node_dir)
    env["OPENCLAW_CONFIG_PATH"] = OPENCLAW_CONFIG_PATH
    env["OPENCLAW_HOME"] = DATA_DIR
    env["OPENCLAW_STATE_DIR"] = OPENCLAW_STATE_DIR
    env["OLLAMA_API_KEY"] = "ollama-local"
    env["OLLAMA_MODELS"] = MODELS_DIR
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_path = OPENCLAW_LOG_PATH
    gateway_cmd = f"\"{openclaw_cmd}\" gateway run --allow-unconfigured --dev --port {GATEWAY_PORT} --bind loopback --verbose"
    process = subprocess.Popen(
        gateway_cmd,
        shell=True,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        stdout=open(log_path, "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
    )
    if wait_for_http_ready(f"http://127.0.0.1:{GATEWAY_PORT}/", timeout=12):
        log("OpenClaw Gateway 已启动")
        return process
    if process.poll() is not None:
        log("OpenClaw Gateway 启动失败，尝试兼容模式")
        log_tail = read_tail(log_path, 12)
        if log_tail:
            log("OpenClaw 启动日志:")
            for line in log_tail:
                log(line)
    compat_cmd = f"\"{openclaw_cmd}\" gateway run --allow-unconfigured --dev --bind loopback --verbose"
    process = subprocess.Popen(
        compat_cmd,
        shell=True,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        stdout=open(log_path, "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
    )
    if wait_for_http_ready(f"http://127.0.0.1:{GATEWAY_PORT}/", timeout=12):
        log("OpenClaw Gateway 已启动")
        return process
    if process.poll() is not None:
        log_tail = read_tail(log_path, 12)
        if log_tail:
            log("OpenClaw 启动日志:")
            for line in log_tail:
                log(line)
        raise RuntimeError("OpenClaw 启动失败")
    log("OpenClaw 已启动，但控制台暂未响应，可稍后点击打开控制台。")
    return process


def is_http_available(url, timeout=2):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status < 500
    except Exception:
        return False


def wait_for_http_ready(url, timeout=12):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_http_available(url, timeout=2):
            return True
        time.sleep(1)
    return False


def read_tail(path, max_lines=10):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]
    return lines[-max_lines:]


def terminate_process(process):
    if process.poll() is not None:
        return
    try:
        subprocess.run(f"taskkill /PID {process.pid} /T /F", shell=True, capture_output=True)
    except Exception:
        pass


def terminate_process_by_port(port, log):
    try:
        result = subprocess.run("netstat -ano", shell=True, capture_output=True, text=True)
    except Exception:
        return
    pids = set()
    for line in (result.stdout or "").splitlines():
        text = line.strip()
        if not text:
            continue
        if f":{port} " not in text and not text.endswith(f":{port}"):
            continue
        parts = text.split()
        if len(parts) < 5:
            continue
        pid = parts[-1]
        if pid.isdigit():
            pids.add(pid)
    for pid in pids:
        try:
            subprocess.run(f"taskkill /PID {pid} /T /F", shell=True, capture_output=True)
            log(f"已结束端口 {port} 的进程 PID {pid}")
        except Exception:
            pass


if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
