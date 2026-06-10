"""
CLI tests for main.py - command line interface testing.
"""

import subprocess
import sys
import os
import pytest


class TestCLIHelp:
    def test_help_flag_returns_zero(self):
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_help_flag_shows_usage(self):
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            capture_output=True,
            text=True,
        )
        output = result.stdout.lower()
        assert "python main.py" in output or "usage" in output


class TestCLIVersion:
    def test_version_flag_returns_zero(self):
        result = subprocess.run(
            [sys.executable, "main.py", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_version_flag_shows_version(self):
        result = subprocess.run(
            [sys.executable, "main.py", "--version"],
            capture_output=True,
            text=True,
        )
        output = result.stdout
        assert "version" in output.lower()
        assert "1.2.0" in output


class TestCLIInvalidArgs:
    def test_invalid_argument_returns_error(self):
        result = subprocess.run(
            [sys.executable, "main.py", "--invalid-arg"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0

    def test_invalid_argument_shows_error_message(self):
        result = subprocess.run(
            [sys.executable, "main.py", "--invalid-arg"],
            capture_output=True,
            text=True,
        )
        assert "error" in result.stderr.lower() or "错误" in result.stderr

    def test_too_many_arguments_returns_error(self):
        result = subprocess.run(
            [sys.executable, "main.py", "arg1", "arg2"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0


class TestCLIEmptyInput:
    def test_empty_input_shows_prompt(self):
        result = subprocess.run(
            [sys.executable, "main.py"],
            input="\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert (
            result.returncode != 0
            or "请输入" in result.stdout
            or "有效" in result.stdout
        )

    def test_empty_input_does_not_crash(self):
        result = subprocess.run(
            [sys.executable, "main.py"],
            input="\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert "traceback" not in result.stderr.lower()


class TestCLIInterrupt:
    def test_keyboard_interrupt_handled(self):
        result = subprocess.run(
            [sys.executable, "main.py"],
            input="quit\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert "再见" in result.stdout


class TestCLILocalDemoMode:
    def test_missing_models_config_starts_local_demo_mode(self, tmp_path):
        missing_config = tmp_path / "missing-models.json"
        env = os.environ.copy()
        env["YICE_MODELS_CONFIG"] = str(missing_config)

        result = subprocess.run(
            [sys.executable, "main.py"],
            input="quit\n",
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )

        assert result.returncode == 0
        assert "本地演示模式" in result.stdout
        assert "无需 API Key" in result.stdout
        assert "core.data_loader - INFO" not in result.stdout

    def test_placeholder_models_config_starts_local_demo_mode(self, tmp_path):
        config_path = tmp_path / "models.json"
        config_path.write_text(
            """{
  "providers": {
    "deepseek": {
      "api_key": "your-api-key-here",
      "base_url": "https://api.deepseek.com",
      "default_model": "deepseek-v4-flash"
    }
  },
  "agents": {
    "scene_router": {"provider": "deepseek", "model": "deepseek-v4-flash"}
  }
}""",
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["YICE_MODELS_CONFIG"] = str(config_path)

        result = subprocess.run(
            [sys.executable, "main.py"],
            input="quit\n",
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )

        assert result.returncode == 0
        assert "配置未启用" in result.stdout
        assert "本地演示模式" in result.stdout
