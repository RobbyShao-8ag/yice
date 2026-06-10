#!/usr/bin/env python3
"""
易策 (yice) Web 应用统一启动脚本

功能：
- 一键启动后端 FastAPI 服务
- 自动启动前端开发服务器
- 自动打开浏览器

使用方法:
    python web/main.py

环境变量:
    YICE_BACKEND_PORT: 后端端口 (默认：8000)
    YICE_FRONTEND_PORT: 前端端口 (默认：5173)
    YICE_BACKEND_HOST: 后端监听地址 (默认：127.0.0.1)
    YICE_FRONTEND_HOST: 前端监听地址 (默认：127.0.0.1)
    YICE_NO_OPEN: 不自动打开浏览器
"""

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def get_project_root() -> Path:
    """获取项目根目录 (yice 目录)."""
    return Path(__file__).parent.parent


def get_backend_path() -> Path:
    """获取后端目录."""
    return Path(__file__).parent / "backend"


def get_frontend_path() -> Path:
    """获取前端目录."""
    return Path(__file__).parent / "frontend"


def get_backend_python(backend_path: Path) -> Path:
    """Return the backend venv Python executable path."""
    candidates = [
        backend_path / "venv" / "bin" / "python",
        backend_path / "venv" / "Scripts" / "python.exe",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "未找到后端虚拟环境中的 Python 解释器。请重新运行 ./setup.sh，"
        "或手动执行：cd web/backend && rm -rf venv && python3 -m venv venv "
        "&& source venv/bin/activate && pip install -r requirements.txt"
    )


def build_backend_command(venv_python: Path, port: int, host: str) -> list[str]:
    """Build backend server command."""
    command = [
        str(venv_python),
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    if os.getenv("YICE_BACKEND_RELOAD", "").lower() in ("1", "true", "yes"):
        command.append("--reload")

    return command


def build_frontend_command(frontend_path: Path, port: int, host: str) -> list[str]:
    """Build frontend dev server command without relying on .bin execute bits."""
    vite_entrypoint = frontend_path / "node_modules" / "vite" / "bin" / "vite.js"
    if vite_entrypoint.exists():
        return ["node", str(vite_entrypoint), "--host", host, "--port", str(port)]
    return ["npm", "run", "dev", "--", "--host", host, "--port", str(port)]


def check_venv() -> bool:
    """检查后端虚拟环境是否存在."""
    backend_path = get_backend_path()
    venv_path = backend_path / "venv"

    if not venv_path.exists():
        print("❌ 后端虚拟环境不存在")
        print(
            "请先运行：cd web/backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        )
        return False

    try:
        get_backend_python(backend_path)
    except FileNotFoundError as e:
        print("❌ 后端虚拟环境不完整")
        print(str(e))
        return False

    return True


def check_node_modules() -> bool:
    """检查前端 node_modules 是否存在."""
    frontend_path = get_frontend_path()
    node_modules_path = frontend_path / "node_modules"

    if not node_modules_path.exists():
        print("❌ 前端依赖未安装")
        print("请先运行：cd web/frontend && npm install")
        return False

    return True


def start_backend(port: int, host: str) -> subprocess.Popen:
    """启动后端 FastAPI 服务."""
    backend_path = get_backend_path()
    venv_python = get_backend_python(backend_path)

    env = os.environ.copy()
    env["PORT"] = str(port)

    print(f"🚀 启动后端服务 ({host}:{port})...")

    process = subprocess.Popen(
        build_backend_command(venv_python, port, host),
        cwd=str(backend_path),
        env=env,
    )

    return process


def start_frontend(port: int, host: str) -> subprocess.Popen:
    """启动前端开发服务器."""
    frontend_path = get_frontend_path()

    env = os.environ.copy()
    env["PORT"] = str(port)

    print(f"🎨 启动前端服务 ({host}:{port})...")

    process = subprocess.Popen(
        build_frontend_command(frontend_path, port, host),
        cwd=str(frontend_path),
        env=env,
    )

    return process


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """等待服务器启动."""
    import urllib.error
    import urllib.request

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)

    return False


def main():
    """主函数."""
    print("=" * 60)
    print("🌟 易策 (yice) Web 应用启动器 🌟")
    print("=" * 60)

    # 获取项目根目录
    project_root = get_project_root()
    os.chdir(project_root)

    # 检查依赖
    print("\n📋 检查环境...")

    if not check_venv():
        sys.exit(1)

    if not check_node_modules():
        sys.exit(1)

    print("✅ 环境检查通过")

    # 获取端口配置
    backend_port = int(os.getenv("YICE_BACKEND_PORT", "8000"))
    frontend_port = int(os.getenv("YICE_FRONTEND_PORT", "5173"))
    backend_host = os.getenv("YICE_BACKEND_HOST", "127.0.0.1")
    frontend_host = os.getenv("YICE_FRONTEND_HOST", "127.0.0.1")
    no_open = os.getenv("YICE_NO_OPEN", "").lower() in ("1", "true", "yes")

    # 启动后端
    backend_process = start_backend(backend_port, backend_host)

    # 等待后端启动
    print("⏳ 等待后端服务就绪...")
    if wait_for_server(f"http://{backend_host}:{backend_port}/api/health"):
        print("✅ 后端服务已就绪")
    else:
        print("⚠️  后端服务启动超时，但将继续启动前端")

    # 启动前端
    frontend_process = start_frontend(frontend_port, frontend_host)

    # 等待前端启动
    print("⏳ 等待前端服务就绪...")
    if wait_for_server(f"http://{frontend_host}:{frontend_port}"):
        print("✅ 前端服务已就绪")
    else:
        print("⚠️  前端服务启动超时")

    # 打开浏览器
    if not no_open:
        print("\n🌐 打开浏览器...")
        webbrowser.open(f"http://{frontend_host}:{frontend_port}")

    print("\n" + "=" * 60)
    print("✨ 易策 Web 应用已启动!")
    print("=" * 60)
    print(f"📍 前端地址：http://{frontend_host}:{frontend_port}")
    print(f"🔌 后端地址：http://{backend_host}:{backend_port}")
    print("\n按 Ctrl+C 停止所有服务")
    print("=" * 60 + "\n")

    # 等待进程结束
    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.wait()
        frontend_process.wait()
        print("✅ 所有服务已停止")


if __name__ == "__main__":
    main()
