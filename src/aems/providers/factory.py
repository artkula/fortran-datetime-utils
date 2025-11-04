"""
Provider factory for creating LLM provider instances.

Handles provider selection and configuration from settings.
"""

import logging
from typing import Optional

from aems.providers.base import LLMProvider, ProviderType
from aems.providers.claude import ClaudeProvider
from aems.config import get_config

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating LLM provider instances."""

    @staticmethod
    def create_provider(
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMProvider:
        """
        Create an LLM provider instance.

        Args:
            provider_type: Provider type (claude, openai, gemini, local)
            api_key: API key (if None, loaded from config)
            model: Model identifier (if None, uses provider default)
            temperature: Temperature (if None, uses config)
            max_tokens: Max tokens (if None, uses config)

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If provider type is unsupported
        """
        config = get_config()

        # Use config values as defaults
        provider_type = provider_type or config.provider
        temperature = temperature if temperature is not None else config.temperature
        max_tokens = max_tokens if max_tokens is not None else config.max_tokens

        # Get API key from config if not provided
        if api_key is None:
            api_key = config.get_api_key()

        provider_type_lower = provider_type.lower()

        if provider_type_lower == ProviderType.CLAUDE:
            return ClaudeProvider(
                api_key=api_key,
                model=model or config.model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        elif provider_type_lower == ProviderType.OPENAI:
            # TODO: Implement OpenAI provider
            raise NotImplementedError("OpenAI provider not yet implemented")

        elif provider_type_lower == ProviderType.GEMINI:
            # TODO: Implement Gemini provider
            raise NotImplementedError("Gemini provider not yet implemented")

        elif provider_type_lower == ProviderType.LOCAL:
            # TODO: Implement local model provider
            raise NotImplementedError("Local provider not yet implemented")

        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    @staticmethod
    def create_default_provider() -> LLMProvider:
        """
        Create a provider using default configuration.

        Returns:
            LLMProvider instance configured from settings
        """
        return ProviderFactory.create_provider()


# Convenience function
def get_provider(
    provider_type: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """
    Get an LLM provider instance.

    Args:
        provider_type: Provider type (claude, openai, gemini, local)
        **kwargs: Additional provider configuration

    Returns:
        LLMProvider instance
    """
    return ProviderFactory.create_provider(provider_type, **kwargs)
