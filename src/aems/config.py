"""
Configuration management for AEMS using Pydantic Settings.

Loads configuration from environment variables and .env files.
"""

from pathlib import Path
from typing import Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AEMSConfig(BaseSettings):
    """
    AEMS configuration loaded from environment variables.

    Supports .env file loading and validation.
    """

    model_config = SettingsConfigDict(
        env_prefix="AEMS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Provider settings
    provider: Literal["claude", "openai", "gemini", "local"] = Field(
        default="claude",
        description="LLM provider to use for grading"
    )

    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key for Claude"
    )

    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )

    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Google Gemini API key"
    )

    # Model settings
    model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Model identifier"
    )

    temperature: float = Field(
        default=0.2,
        ge=0,
        le=2,
        description="Sampling temperature for grading (0-2)"
    )

    max_tokens: int = Field(
        default=4096,
        ge=1,
        description="Maximum tokens in LLM response"
    )

    # OCR settings
    ocr_engine: Literal["tesseract", "doctr", "trocr", "pix2tex", "mathpix"] = Field(
        default="tesseract",
        description="Primary OCR engine"
    )

    tesseract_lang: str = Field(
        default="eng",
        description="Tesseract language codes (e.g., 'eng+swe')"
    )

    ocr_dpi: int = Field(
        default=300,
        ge=150,
        le=600,
        description="DPI for PDF rasterization"
    )

    # Layout detection
    layout_model: Literal["layoutparser-d2", "marker", "surya"] = Field(
        default="marker",
        description="Layout detection model"
    )

    # Privacy settings
    pseudonymize: bool = Field(
        default=True,
        description="Pseudonymize student identifiers in API calls"
    )

    local_only: bool = Field(
        default=False,
        description="Run fully locally (no external API calls)"
    )

    # Paths
    data_dir: Path = Field(
        default=Path("./data"),
        description="Data directory for storing processed files"
    )

    gold_dir: Path = Field(
        default=Path("./gold"),
        description="Directory for gold materials"
    )

    output_dir: Path = Field(
        default=Path("./output"),
        description="Default output directory"
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level"
    )

    log_file: Optional[Path] = Field(
        default=None,
        description="Log file path (None = console only)"
    )

    # Performance
    batch_size: int = Field(
        default=10,
        ge=1,
        description="Batch size for processing student submissions"
    )

    max_workers: int = Field(
        default=4,
        ge=1,
        description="Maximum parallel workers"
    )

    def get_api_key(self) -> Optional[str]:
        """Get API key for the configured provider."""
        if self.provider == "claude":
            return self.anthropic_api_key
        elif self.provider == "openai":
            return self.openai_api_key
        elif self.provider == "gemini":
            return self.gemini_api_key
        return None

    def ensure_dirs(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.gold_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
_config: Optional[AEMSConfig] = None


def get_config() -> AEMSConfig:
    """
    Get the global configuration instance.

    Returns:
        AEMSConfig instance
    """
    global _config
    if _config is None:
        _config = AEMSConfig()
    return _config


def reload_config() -> AEMSConfig:
    """
    Reload configuration from environment.

    Returns:
        New AEMSConfig instance
    """
    global _config
    _config = AEMSConfig()
    return _config
