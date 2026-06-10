"""Tests for configuration validation."""

from core.config_validator import ConfigValidator


def test_validator_rejects_agent_model_not_listed_by_provider():
    config = {
        "providers": {
            "deepseek": {
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com",
                "models": ["deepseek-v4-flash"],
            }
        },
        "agents": {
            "reporter": {
                "provider": "deepseek",
                "model": "deepseek-v4-pro",
            }
        },
    }

    validator = ConfigValidator(config)

    assert validator.validate() is False
    assert any("not listed" in error for error in validator.errors)


def test_validator_allows_provider_without_model_allowlist():
    config = {
        "providers": {
            "deepseek": {
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com",
                "default_model": "deepseek-v4-flash",
            }
        },
        "agents": {
            "reporter": {
                "provider": "deepseek",
                "model": "deepseek-v4-pro",
            }
        },
    }

    validator = ConfigValidator(config)

    assert validator.validate() is True


def test_validator_rejects_common_placeholder_api_keys():
    config = {
        "providers": {
            "deepseek": {
                "api_key": "your-api-key-here",
                "base_url": "https://api.deepseek.com",
                "default_model": "deepseek-v4-flash",
            },
            "openai": {
                "api_key": "YOUR_API_KEY",
                "base_url": "https://api.openai.com",
                "default_model": "gpt-4o-mini",
            },
        },
        "agents": {
            "scene_router": {
                "provider": "deepseek",
                "model": "deepseek-v4-flash",
            }
        },
    }

    validator = ConfigValidator(config)

    assert validator.validate() is False
    assert any("placeholder API key" in error for error in validator.errors)
