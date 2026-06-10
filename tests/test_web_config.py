"""Tests for Web configuration routes."""

from web.backend.routes.config import _mask_config


def test_mask_config_redacts_provider_api_keys_without_mutating_source():
    config = {
        "providers": {
            "openai": {
                "api_key": "sk-1234567890abcdef",
                "base_url": "https://api.example.com",
            },
            "empty": {
                "api_key": "",
                "base_url": "https://api.empty.com",
            },
        },
        "agents": {
            "reporter": {
                "provider": "openai",
                "model": "test-model",
            }
        },
    }

    masked = _mask_config(config)

    assert masked["providers"]["openai"]["api_key"] == "sk-...cdef"
    assert masked["providers"]["empty"]["api_key"] == ""
    assert config["providers"]["openai"]["api_key"] == "sk-1234567890abcdef"
