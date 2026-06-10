"""Tests for the Web application launcher."""

import importlib.util
from pathlib import Path


def load_web_main():
    module_path = Path(__file__).resolve().parents[1] / "web" / "main.py"
    spec = importlib.util.spec_from_file_location("web_launcher_main", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_get_backend_python_uses_unix_venv_python(tmp_path):
    web_main = load_web_main()
    backend_path = tmp_path / "backend"
    python_path = backend_path / "venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.touch()

    assert web_main.get_backend_python(backend_path) == python_path


def test_get_backend_python_raises_when_venv_has_no_python(tmp_path):
    web_main = load_web_main()
    backend_path = tmp_path / "backend"
    (backend_path / "venv" / "bin").mkdir(parents=True)

    try:
        web_main.get_backend_python(backend_path)
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError as exc:
        assert "venv" in str(exc)
        assert "python" in str(exc)


def test_build_backend_command_omits_reload_by_default(tmp_path, monkeypatch):
    web_main = load_web_main()
    python_path = tmp_path / "python"
    monkeypatch.delenv("YICE_BACKEND_RELOAD", raising=False)

    command = web_main.build_backend_command(python_path, 8000, "127.0.0.1")

    assert str(python_path) == command[0]
    assert command[command.index("--host") + 1] == "127.0.0.1"
    assert "--reload" not in command


def test_build_frontend_command_uses_node_vite_entrypoint(tmp_path):
    web_main = load_web_main()
    frontend_path = tmp_path / "frontend"
    vite_path = frontend_path / "node_modules" / "vite" / "bin" / "vite.js"
    vite_path.parent.mkdir(parents=True)
    vite_path.touch()

    command = web_main.build_frontend_command(frontend_path, 5173, "127.0.0.1")

    assert command == [
        "node",
        str(vite_path),
        "--host",
        "127.0.0.1",
        "--port",
        "5173",
    ]
