"""LLM Client for making API calls to LLM providers."""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from core.errors import LLMCallError, LLMRateLimitError

logger = logging.getLogger(__name__)


def _log_raw_response(provider: str, model: str, request_payload: dict, response_body: str) -> None:
    """Log raw LLM request and response to file.
    
    Args:
        provider: LLM provider name
        model: Model name
        request_payload: The request payload sent to API
        response_body: Raw response body from API
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    log_file = os.path.join(log_dir, f"llm_raw_{timestamp}.json")
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
        "request": request_payload,
        "response_raw": response_body,
    }
    
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_entry, f, ensure_ascii=False, indent=2)
        logger.debug(f"Raw LLM response logged to: {log_file}")
    except Exception as e:
        logger.warning(f"Failed to log raw LLM response: {e}")


def _filter_think_blocks(content: str) -> str:
    """Filter out think/reasoning blocks from LLM response.
    
    Handles MiniMax's hlen...hlen think block format.
    Also handles common think markers like <|think|>, <think|, etc.
    
    Args:
        content: Raw content from LLM response.
        
    Returns:
        Filtered content without think blocks.
    """
    import re
    
    original_content = content
    
    # Pattern 1: hlen...hlen blocks (MiniMax format)
    # Matches: hlen\n<think content>\nhlen
    content = re.sub(
        r'hlen\s*\n.*?\n\s*hlen\s*\n?',
        '',
        content,
        flags=re.DOTALL,
    )
    
    # Pattern 2: <think>...</think> or <|think|>...<|/think|>
    content = re.sub(
        r'<\|?think\|?>.*?<\|?/think\|?>',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    
    # Pattern 2b: <think>... (without closing tag, MiniMax format)
    content = re.sub(
        r'<think>.*?(?=(?:\n\n|\Z))',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    
    # Pattern 3: <think|...|think> or hlen|...|hlen
    content = re.sub(
        r'(hlen|think)\|.*?\|(hlen|think)',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    
    # Pattern 4: Standalone hlen markers
    lines = content.split('\n')
    filtered_lines = []
    in_think_block = False
    
    for line in lines:
        stripped = line.strip().lower()
        
        # Detect think block boundaries
        if stripped == 'hlen' or stripped == '|hlen|' or stripped == 'hlen|':
            in_think_block = not in_think_block
            continue
        
        # Skip lines inside think block
        if in_think_block:
            continue
        
        # Skip lines that are just think markers
        if stripped in ['hlen', '|hlen|', 'hlen|', '|hlen', 'think', '|think|']:
            continue
        
        filtered_lines.append(line)
    
    content = '\n'.join(filtered_lines)
    
    # Clean up excessive newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    if len(content) < len(original_content):
        logger.info(f"Filtered think blocks: {len(original_content)} -> {len(content)} chars")
    
    return content.strip()


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: str
    api_key: str
    base_url: str = "https://api.openai.com"
    model: str = "gpt-3.5-turbo"
    timeout: int = 60
    max_retries: int = 3


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
                    return self._parse_response(response, payload)

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

    def _parse_response(self, response, request_payload: dict) -> str:
        body = response.read().decode("utf-8")

        if not body:
            raise ValueError("Empty response body")

        # Log raw request and response to file
        _log_raw_response(
            provider=self._config.provider,
            model=self._config.model,
            request_payload=request_payload,
            response_body=body
        )

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")

        # DEBUG: Log full response structure
        logger.info("=" * 60)
        logger.info("LLM RAW RESPONSE:")
        try:
            logger.info(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        except:
            logger.info(str(data)[:2000])
        logger.info("=" * 60)

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

        content = _filter_think_blocks(content)

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
        FileNotFoundError: If config file doesn't exist and example file not found.
    """
    if not os.path.exists(config_path):
        example_path = "models.example.json"
        if os.path.exists(example_path):
            import shutil
            shutil.copy(example_path, config_path)
            logger.info(f"Copied {example_path} to {config_path}")
        else:
            raise FileNotFoundError(
                f"Config file not found: {config_path}. "
                f"Please create it from models.example.json"
            )

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
