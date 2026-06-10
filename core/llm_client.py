"""LLM Client for making API calls to LLM providers."""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from core.errors import LLMCallError, LLMRateLimitError
from core.llm_filters import filter_think_content

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: str
    api_key: str
    base_url: str = "https://api.openai.com"
    model: str = "gpt-3.5-turbo"
    timeout: int = 60
    max_retries: int = 3
    log_raw_response: bool = False


class LLMClient:
    """Client for making API calls to LLM providers.

    Supports OpenAI-compatible APIs with retry logic and error handling.
    """

    def __init__(self, config: LLMConfig):
        self._config = config

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        response_format: Optional[dict[str, str]] = None,
    ) -> str:
        """Make a chat completion request.

        Args:
            system_prompt: System prompt.
            user_prompt: User prompt.
            temperature: Sampling temperature (0-2).
            response_format: Optional response format for JSON output.

        Returns:
            Response content as string.

        Raises:
            LLMRateLimitError: When API returns 429.
            urllib.error.HTTPError: For other HTTP errors.
        """
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        if response_format:
            payload["response_format"] = response_format

        return self._make_request(payload)

    def _make_request(self, payload: dict[str, Any]) -> str:
        """Make HTTP request with retry logic.

        Args:
            payload: Request payload.

        Returns:
            Response content.

        Raises:
            LLMRateLimitError: When API returns 429.
            LLMCallError: When all retries are exhausted.
            urllib.error.HTTPError: For other HTTP errors.
        """
        url = f"{self._config.base_url}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}",
        }

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        max_retries = self._config.max_retries
        base_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(
                    request, timeout=self._config.timeout
                ) as response:
                    return self._parse_response(response)

            except urllib.error.HTTPError as e:
                # Handle rate limit (429) - raise immediately
                if e.code == 429:
                    retry_after = self._parse_retry_after(e.headers)
                    raise LLMRateLimitError(
                        retry_after=retry_after, provider=self._config.provider
                    )

                # Don't retry client errors (4xx except 429)
                if 400 <= e.code < 500:
                    raise

                # Retry server errors (5xx)
                if attempt == max_retries - 1:
                    raise LLMCallError(
                        f"Server error {e.code} after {max_retries} retries",
                        original_error=e,
                    )
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Server error {e.code}, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)

            except (TimeoutError, urllib.error.URLError) as e:
                if attempt == max_retries - 1:
                    raise LLMCallError(
                        f"Network error after {max_retries} retries: {e}",
                        original_error=e,
                    )
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Network error, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)

        raise LLMCallError("Max retries exceeded")

    def _parse_response(self, response) -> str:
        body = response.read().decode("utf-8")

        if not body:
            raise ValueError("Empty response body")

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")

        usage = data.get("usage", {})
        logger.debug(
            "LLM response received provider=%s model=%s prompt_tokens=%s "
            "completion_tokens=%s total_tokens=%s",
            self._config.provider,
            self._config.model,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("total_tokens"),
        )

        if self._config.log_raw_response or os.getenv("YICE_DEBUG_LLM_RAW") == "1":
            logger.debug("LLM raw response: %s", _safe_json_preview(data))

        # Extract message content
        if "choices" not in data or not data["choices"]:
            raise ValueError("Invalid response: missing choices")

        choice = data["choices"][0]
        if "message" not in choice:
            raise ValueError("Invalid response: missing message")

        message = choice["message"]
        if "content" not in message:
            raise ValueError("Invalid response: missing content")

        content = message["content"]

        original_content = content
        content = filter_think_content(content)

        if len(content) < len(original_content):
            logger.debug(
                "Filtered LLM reasoning markers: %s -> %s chars",
                len(original_content),
                len(content),
            )

        return content.strip()

    def _parse_retry_after(self, headers) -> Optional[int]:
        """Parse Retry-After header from response.

        Args:
            headers: Response headers.

        Returns:
            Retry duration in seconds, or None if not present.
        """
        retry_after = headers.get("Retry-After")
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                pass
        return None


def load_config(config_path: str = "models.json") -> dict:
    """Load configuration from file and environment.

    Environment variables:
        YICE_DEFAULT_PROVIDER: Override default provider
        YICE_{PROVIDER}_API_KEY: Override provider API key
        YICE_{PROVIDER}_BASE_URL: Override provider base URL
        YICE_{AGENT}_MODEL: Override agent model

    Args:
        config_path: Path to config file.

    Returns:
        Configuration dictionary with providers and agents.

    Raises:
        FileNotFoundError: If config file doesn't exist.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Override with environment variables
    if os.getenv("YICE_DEFAULT_PROVIDER"):
        config["default_provider"] = os.getenv("YICE_DEFAULT_PROVIDER")

    providers = config.get("providers", {})
    for provider_name in providers.keys():
        env_api_key = os.getenv(f"YICE_{provider_name.upper()}_API_KEY")
        if env_api_key:
            providers[provider_name]["api_key"] = env_api_key

        env_base_url = os.getenv(f"YICE_{provider_name.upper()}_BASE_URL")
        if env_base_url:
            providers[provider_name]["base_url"] = env_base_url

    agents = config.get("agents", {})
    for agent_name in agents.keys():
        env_model = os.getenv(f"YICE_{agent_name.upper()}_MODEL")
        if env_model:
            agents[agent_name]["model"] = env_model

    return config


def _safe_json_preview(data: Any, limit: int = 2000) -> str:
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)[:limit]
    except (TypeError, ValueError):
        return str(data)[:limit]
