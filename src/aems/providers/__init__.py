"""
LLM provider adapters.

Supports multiple backends:
- Claude (Anthropic)
- OpenAI (future)
- Gemini (future)
- Local models (future)
"""

from aems.providers.base import (
    LLMProvider,
    LLMMessage,
    LLMResponse,
    ProviderType,
    ProviderError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from aems.providers.claude import ClaudeProvider, create_claude_provider
from aems.providers.factory import ProviderFactory, get_provider

__all__ = [
    "LLMProvider",
    "LLMMessage",
    "LLMResponse",
    "ProviderType",
    "ProviderError",
    "ProviderAuthError",
    "ProviderRateLimitError",
    "ProviderTimeoutError",
    "ClaudeProvider",
    "create_claude_provider",
    "ProviderFactory",
    "get_provider",
]
