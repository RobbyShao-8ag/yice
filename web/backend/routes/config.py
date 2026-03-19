import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()

# 配置文件路径（相对于 CLI 项目根目录）
CONFIG_FILE = Path(__file__).parent.parent.parent.parent / "models.json"


def _load_config() -> dict[str, Any]:
    """Load configuration from file."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_config(config: dict[str, Any]) -> None:
    """Save configuration to file."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


@router.get("/")
async def get_config() -> dict[str, Any]:
    """Get current system configuration."""
    try:
        config = _load_config()
        return {
            "status": "ok",
            "config": config,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="配置文件不存在")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="配置文件格式错误")


@router.put("/")
async def update_config(config: dict[str, Any]) -> dict[str, Any]:
    """Update system configuration."""
    if not config:
        raise HTTPException(status_code=400, detail="配置不能为空")

    # Validate config structure
    if "providers" not in config:
        raise HTTPException(status_code=400, detail="配置必须包含 providers")

    if "agents" not in config:
        raise HTTPException(status_code=400, detail="配置必须包含 agents")

    # Validate providers
    for provider_name, provider_config in config["providers"].items():
        if not isinstance(provider_config, dict):
            raise HTTPException(
                status_code=400, detail=f"provider '{provider_name}' 配置格式错误"
            )
        if "api_key" not in provider_config:
            raise HTTPException(
                status_code=400, detail=f"provider '{provider_name}' 缺少 api_key"
            )
        if "base_url" not in provider_config:
            raise HTTPException(
                status_code=400, detail=f"provider '{provider_name}' 缺少 base_url"
            )

    # Validate agents
    for agent_name, agent_config in config["agents"].items():
        if not isinstance(agent_config, dict):
            raise HTTPException(
                status_code=400, detail=f"agent '{agent_name}' 配置格式错误"
            )
        if "provider" not in agent_config:
            raise HTTPException(
                status_code=400, detail=f"agent '{agent_name}' 缺少 provider"
            )
        provider = agent_config["provider"]
        if provider not in config["providers"]:
            raise HTTPException(
                status_code=400,
                detail=f"agent '{agent_name}' 引用了不存在的 provider '{provider}'",
            )

    try:
        _save_config(config)
        return {"status": "ok", "message": "配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败：{str(e)}")


@router.post("/test")
async def test_connection(
    provider_name: str, model: str, api_key: str, base_url: str
) -> dict[str, Any]:
    """Test LLM API connection."""
    if not provider_name or not model or not api_key or not base_url:
        raise HTTPException(status_code=400, detail="缺少必要的参数")

    # Build test request
    url = f"{base_url}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "Please reply with 'OK' to confirm connection.",
            },
        ],
        "temperature": 0.5,
        "max_tokens": 10,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            result = json.loads(body)

            if "choices" in result and len(result["choices"]) > 0:
                return {
                    "status": "ok",
                    "message": "连接测试成功",
                    "response": result["choices"][0]["message"]["content"],
                }
            else:
                raise HTTPException(status_code=500, detail="API 响应格式异常")

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise HTTPException(
            status_code=e.code,
            detail=f"HTTP 错误 {e.code}: {error_body}",
        )
    except urllib.error.URLError as e:
        raise HTTPException(status_code=500, detail=f"网络错误：{str(e.reason)}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="API 响应格式错误")
    except TimeoutError:
        raise HTTPException(status_code=500, detail="请求超时")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试失败：{str(e)}")
