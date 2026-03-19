"""Tests for LLM client."""

import json
import pytest
from unittest.mock import MagicMock, patch, mock_open
import urllib.error

from core.llm_client import LLMClient, LLMConfig, load_config
from core.errors import LLMRateLimitError


class TestLLMClient:
    """Tests for LLMClient class."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return LLMConfig(
            provider="openai",
            api_key="test-key",
            base_url="https://api.test.com",
            model="test-model",
            timeout=30,
            max_retries=3,
        )

    @pytest.fixture
    def client(self, config):
        """Create test client."""
        return LLMClient(config)

    def test_chat_success(self, client, mocker):
        """Test successful chat request."""
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "test response"}}]}
        ).encode()

        mocker.patch("urllib.request.urlopen", return_value=mock_response)

        result = client.chat("system", "user")
        assert result == "test response"

    def test_401_unauthorized(self, client, mocker):
        """Test 401 Unauthorized error."""
        mock_error = urllib.error.HTTPError(
            url="https://api.test.com", code=401, msg="Unauthorized", hdrs={}, fp=None
        )

        mocker.patch("urllib.request.urlopen", side_effect=mock_error)

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            client.chat("system", "user")
        assert exc_info.value.code == 401

    def test_403_forbidden(self, client, mocker):
        """Test 403 Forbidden error."""
        mock_error = urllib.error.HTTPError(
            url="https://api.test.com", code=403, msg="Forbidden", hdrs={}, fp=None
        )

        mocker.patch("urllib.request.urlopen", side_effect=mock_error)

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            client.chat("system", "user")
        assert exc_info.value.code == 403

    def test_500_server_error(self, client, mocker):
        """Test 500 Server Error with retry."""
        mock_error = urllib.error.HTTPError(
            url="https://api.test.com",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )

        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "success after retry"}}]}
        ).encode()

        mocker.patch(
            "urllib.request.urlopen",
            side_effect=[mock_error, mock_error, mock_response],
        )

        result = client.chat("system", "user")
        assert result == "success after retry"

    def test_429_rate_limit_raises_error(self, client, mocker):
        """Test 429 rate limit raises LLMRateLimitError."""
        hdrs = {"Retry-After": "60"}
        mock_error = urllib.error.HTTPError(
            url="https://api.test.com", code=429, msg="Rate Limit", hdrs=hdrs, fp=None
        )

        mocker.patch("urllib.request.urlopen", side_effect=mock_error)

        with pytest.raises(LLMRateLimitError) as exc_info:
            client.chat("system", "user")
        assert exc_info.value.retry_after == 60
        assert exc_info.value.provider == "openai"

    def test_429_rate_limit_no_retry_header(self, client, mocker):
        """Test 429 without Retry-After header."""
        hdrs = {}
        mock_error = urllib.error.HTTPError(
            url="https://api.test.com", code=429, msg="Rate Limit", hdrs=hdrs, fp=None
        )

        mocker.patch("urllib.request.urlopen", side_effect=mock_error)

        with pytest.raises(LLMRateLimitError) as exc_info:
            client.chat("system", "user")
        assert exc_info.value.retry_after is None

    def test_retry_logic_triggered(self, client, mocker):
        """Test retry logic is triggered on transient errors."""
        mock_error = urllib.error.HTTPError(
            url="https://api.test.com", code=502, msg="Bad Gateway", hdrs={}, fp=None
        )

        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "recovered"}}]}
        ).encode()

        mocker.patch("urllib.request.urlopen", side_effect=[mock_error, mock_response])

        result = client.chat("system", "user")
        assert result == "recovered"

    def test_empty_response_raises_error(self, client, mocker):
        """Test empty response raises ValueError."""
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = b""

        mocker.patch("urllib.request.urlopen", return_value=mock_response)

        with pytest.raises(ValueError) as exc_info:
            client.chat("system", "user")
        assert "Empty response" in str(exc_info.value)

    def test_invalid_json_response(self, client, mocker):
        """Test non-JSON response raises ValueError."""
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = b"not valid json"

        mocker.patch("urllib.request.urlopen", return_value=mock_response)

        with pytest.raises(ValueError) as exc_info:
            client.chat("system", "user")
        assert "Invalid JSON" in str(exc_info.value)

    def test_missing_choices_in_response(self, client, mocker):
        """Test response missing choices raises ValueError."""
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({}).encode()

        mocker.patch("urllib.request.urlopen", return_value=mock_response)

        with pytest.raises(ValueError) as exc_info:
            client.chat("system", "user")
        assert "missing choices" in str(exc_info.value)

    def test_missing_message_in_choices(self, client, mocker):
        """Test response missing message in choices raises ValueError."""
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({"choices": [{}]}).encode()

        mocker.patch("urllib.request.urlopen", return_value=mock_response)

        with pytest.raises(ValueError) as exc_info:
            client.chat("system", "user")
        assert "missing message" in str(exc_info.value)

    def test_missing_content_in_message(self, client, mocker):
        """Test response missing content in message raises ValueError."""
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps(
            {"choices": [{"message": {}}]}
        ).encode()

        mocker.patch("urllib.request.urlopen", return_value=mock_response)

        with pytest.raises(ValueError) as exc_info:
            client.chat("system", "user")
        assert "missing content" in str(exc_info.value)

    def test_url_error_retry(self, client, mocker):
        """Test URL error triggers retry."""
        mock_url_error = urllib.error.URLError("Connection refused")

        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "recovered"}}]}
        ).encode()

        mocker.patch(
            "urllib.request.urlopen", side_effect=[mock_url_error, mock_response]
        )

        result = client.chat("system", "user")
        assert result == "recovered"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_success(self, mocker):
        """Test successful config loading."""
        config_data = {
            "provider": "openai",
            "api_key": "test-key",
            "model": "gpt-4",
            "base_url": "https://api.test.com",
            "timeout": 30,
            "max_retries": 3,
        }

        mocker.patch("builtins.open", mock_open(read_data=json.dumps(config_data)))
        mocker.patch("os.path.exists", return_value=True)

        config = load_config("test.json")

        assert config["provider"] == "openai"
        assert config["api_key"] == "test-key"
        assert config["model"] == "gpt-4"
        assert config["base_url"] == "https://api.test.com"

    def test_load_config_missing_file(self):
        """Test missing config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.json")

    def test_load_config_missing_required_field(self, mocker):
        """Test missing required field - load_config returns dict, validation done by ConfigValidator."""
        config_data = {"provider": "openai"}  # missing api_key and model

        mocker.patch("builtins.open", mock_open(read_data=json.dumps(config_data)))
        mocker.patch("os.path.exists", return_value=True)

        # load_config returns dict without validation; ConfigValidator handles validation
        config = load_config("test.json")
        assert config["provider"] == "openai"

    def test_load_config_invalid_json(self, mocker):
        """Test invalid JSON raises error."""
        mocker.patch("builtins.open", mock_open(read_data="not json"))
        mocker.patch("os.path.exists", return_value=True)

        with pytest.raises(json.JSONDecodeError):
            load_config("test.json")

    def test_load_config_defaults(self, mocker):
        """Test config with minimal fields - load_config returns dict as-is."""
        config_data = {
            "provider": "openai",
            "api_key": "test-key",
            "model": "gpt-3.5-turbo",
        }

        mocker.patch("builtins.open", mock_open(read_data=json.dumps(config_data)))
        mocker.patch("os.path.exists", return_value=True)

        config = load_config("test.json")

        # load_config returns dict as-is, no defaults applied
        assert config["provider"] == "openai"
        assert config["api_key"] == "test-key"
        assert config["model"] == "gpt-3.5-turbo"
        # Keys not in original dict won't be added
        assert "base_url" not in config


class TestLLMConfig:
    """Tests for LLMConfig dataclass."""

    def test_config_creation(self):
        """Test LLMConfig creation."""
        config = LLMConfig(
            provider="anthropic",
            api_key="sk-ant-test",
            model="claude-3",
            base_url="https://api.anthropic.com",
            timeout=120,
            max_retries=5,
        )

        assert config.provider == "anthropic"
        assert config.api_key == "sk-ant-test"
        assert config.model == "claude-3"
        assert config.base_url == "https://api.anthropic.com"
        assert config.timeout == 120
        assert config.max_retries == 5
