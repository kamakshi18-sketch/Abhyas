"""
Application Settings & Configuration.
Loads settings from environment variables and .env file.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    # LLM Provider: 'gemini', 'nvidia', 'ollama', or 'mock'
    llm_provider: str = "gemini"

    # Google Gemini Configuration
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.6-flash"

    # NVIDIA Nemotron (NIM) Configuration
    nvidia_api_key: Optional[str] = None
    nvidia_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    # Ollama Local Configuration
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # Database Configuration
    database_url: str = "sqlite:///./data/interviews.db"

    # Application Logging
    log_level: str = "INFO"

    # LLM Inference Parameters
    llm_temperature: float = 0.7
    llm_timeout_seconds: int = 60
    max_llm_retries: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of application settings."""
    return Settings()
