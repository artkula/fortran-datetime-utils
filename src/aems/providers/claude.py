"""
Anthropic Claude provider adapter.

Implements the Claude Messages API for grading with proper
temperature control and token counting.
"""

import logging
from typing import Optional, List

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from aems.providers.base import (
    LLMProvider,
    LLMMessage,
    LLMResponse,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderError,
)

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    """
    Anthropic Claude API provider.

    Supports Claude 3.5 Sonnet and other Claude models with
    proper message formatting and token tracking.
    """

    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ):
        """
        Initialize Claude provider.

        Args:
            api_key: Anthropic API key
            model: Model identifier (default: claude-3-5-sonnet-20241022)
            temperature: Temperature 0.0-1.0 (default 0.2 for grading)
            max_tokens: Max tokens in response
        """
        super().__init__(api_key, model or self.DEFAULT_MODEL, temperature, max_tokens)

        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. Install with: pip install anthropic"
            )

        if not api_key:
            raise ProviderAuthError("Claude API key is required")

        self.client = anthropic.Anthropic(api_key=api_key)

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
            system: System message
            temperature: Override temperature
            max_tokens: Override max tokens

        Returns:
            LLMResponse with generated text
        """
        messages = [LLMMessage(role="user", content=prompt)]
        return self.chat(messages, system=system, temperature=temperature, max_tokens=max_tokens)

    def chat(
        self,
        messages: List[LLMMessage],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a response for a chat conversation.

        Args:
            messages: List of messages
            system: System message (optional)
            temperature: Override temperature
            max_tokens: Override max tokens

        Returns:
            LLMResponse with generated text
        """
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        # Convert messages to Anthropic format
        api_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        try:
            # Call Claude API
            kwargs = {
                "model": self.model,
                "max_tokens": tokens,
                "temperature": temp,
                "messages": api_messages,
            }

            if system:
                kwargs["system"] = system

            response = self.client.messages.create(**kwargs)

            # Extract text from response
            text = ""
            if response.content:
                text = response.content[0].text

            return LLMResponse(
                text=text,
                model=response.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                finish_reason=response.stop_reason,
                metadata={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "stop_reason": response.stop_reason,
                },
            )

        except anthropic.AuthenticationError as e:
            logger.error(f"Claude authentication error: {e}")
            raise ProviderAuthError(f"Invalid API key: {e}")

        except anthropic.RateLimitError as e:
            logger.error(f"Claude rate limit error: {e}")
            raise ProviderRateLimitError(f"Rate limit exceeded: {e}")

        except anthropic.APITimeoutError as e:
            logger.error(f"Claude timeout error: {e}")
            raise ProviderTimeoutError(f"Request timeout: {e}")

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise ProviderError(f"Claude API error: {e}")

    def check_availability(self) -> bool:
        """
        Check if Claude is available and configured.

        Returns:
            True if provider is ready
        """
        if not self.api_key:
            return False

        try:
            # Try a minimal API call
            self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
            )
            return True
        except Exception as e:
            logger.debug(f"Claude availability check failed: {e}")
            return False


def create_claude_provider(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> ClaudeProvider:
    """
    Create a Claude provider instance.

    Args:
        api_key: Anthropic API key
        model: Model identifier
        temperature: Temperature for grading
        max_tokens: Max tokens

    Returns:
        ClaudeProvider instance
    """
    return ClaudeProvider(
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
