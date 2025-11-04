"""
Base classes for LLM provider adapters.

Provides a unified interface for different LLM backends (Claude, OpenAI, Gemini, local).
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class ProviderType(str, Enum):
    """Supported LLM providers."""
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    LOCAL = "local"


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    text: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All provider implementations must inherit from this class and
    implement the required methods.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ):
        """
        Initialize LLM provider.

        Args:
            api_key: API key for the provider
            model: Model identifier
            temperature: Sampling temperature (0.0 - 2.0, provider-dependent)
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a completion for a prompt.

        Args:
            prompt: User prompt
            system: System message (provider-dependent support)
            temperature: Override temperature
            max_tokens: Override max tokens

        Returns:
            LLMResponse with generated text
        """
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a response for a chat conversation.

        Args:
            messages: List of messages in conversation
            temperature: Override temperature
            max_tokens: Override max tokens

        Returns:
            LLMResponse with generated text
        """
        pass

    @abstractmethod
    def check_availability(self) -> bool:
        """
        Check if the provider is available and configured.

        Returns:
            True if provider is ready to use
        """
        pass

    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about the provider configuration.

        Returns:
            Dictionary with provider details
        """
        return {
            "provider": self.__class__.__name__,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "has_api_key": bool(self.api_key),
        }


class ProviderError(Exception):
    """Base exception for provider errors."""
    pass


class ProviderAuthError(ProviderError):
    """Authentication/API key error."""
    pass


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded."""
    pass


class ProviderTimeoutError(ProviderError):
    """Request timeout."""
    pass
