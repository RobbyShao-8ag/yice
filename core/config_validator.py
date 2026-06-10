"""Configuration validator for yice."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validate yice configuration."""

    REQUIRED_FIELDS = {
        "providers": ["api_key", "base_url"],
        "agents": ["provider", "model"],
    }
    PLACEHOLDER_API_KEYS = {
        "your-api-key-here",
        "your-key",
        "your_api_key",
        "your-api-key",
        "replace-me",
        "changeme",
        "api-key",
        "sk-your-api-key",
        "sk-your-key",
    }

    def __init__(self, config: dict):
        self.config = config
        self.errors = []
        self.warnings = []

    def validate(self) -> bool:
        """Validate configuration.

        Returns:
            True if valid, False otherwise
        """
        self._validate_providers()
        self._validate_agents()
        self._validate_references()

        if self.errors:
            logger.error(f"Config validation failed: {self.errors}")
            return False

        if self.warnings:
            logger.warning(f"Config warnings: {self.warnings}")

        logger.info("Config validation passed")
        return True

    def _validate_providers(self):
        """Validate provider configurations."""
        providers = self.config.get("providers", {})

        if not providers:
            self.errors.append("No providers configured")
            return

        for name, cfg in providers.items():
            for field in self.REQUIRED_FIELDS["providers"]:
                if field not in cfg:
                    self.errors.append(
                        f"Provider '{name}' missing required field: {field}"
                    )

            api_key = cfg.get("api_key", "")
            if not api_key:
                self.errors.append(f"Provider '{name}' has invalid API key")
            elif self._is_placeholder_api_key(api_key):
                self.errors.append(f"Provider '{name}' has placeholder API key")

            base_url = cfg.get("base_url", "")
            if not base_url.startswith(("http://", "https://")):
                self.errors.append(
                    f"Provider '{name}' has invalid base_url: {base_url}"
                )

    def _is_placeholder_api_key(self, api_key: str) -> bool:
        """Return True when api_key is an example value, not a real credential."""
        normalized = api_key.strip().lower()
        if normalized in self.PLACEHOLDER_API_KEYS:
            return True
        if normalized.startswith("sk-your"):
            return True
        return "your" in normalized and "key" in normalized

    def _validate_agents(self):
        """Validate agent configurations."""
        agents = self.config.get("agents", {})
        providers = self.config.get("providers", {})

        for name, cfg in agents.items():
            for field in self.REQUIRED_FIELDS["agents"]:
                if field not in cfg:
                    self.errors.append(
                        f"Agent '{name}' missing required field: {field}"
                    )

            provider = cfg.get("provider")
            if provider and provider not in providers:
                self.errors.append(
                    f"Agent '{name}' references unknown provider: {provider}"
                )

    def _validate_references(self):
        """Validate cross-references."""
        providers = self.config.get("providers", {})
        agents = self.config.get("agents", {})

        for agent_name, agent_cfg in agents.items():
            provider_name = agent_cfg.get("provider")
            model_name = agent_cfg.get("model")
            provider_cfg = providers.get(provider_name, {})

            if not provider_name or not model_name or not provider_cfg:
                continue

            provider_models = provider_cfg.get("models")
            if isinstance(provider_models, list) and provider_models:
                if model_name not in provider_models:
                    self.errors.append(
                        f"Agent '{agent_name}' model '{model_name}' is not listed "
                        f"for provider '{provider_name}'"
                    )
