import json
from typing import Any, List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment or .env file."""

    app_name: str = "ResearchPilot API"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_origins: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
        alias="FRONTEND_ORIGINS",
    )

    # LLM Settings
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gemini-3.8-flash", alias="LLM_MODEL")
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        alias="GEMINI_BASE_URL",
    )
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Search & Extraction settings
    tavily_api_key: Optional[str] = Field(default=None, alias="TAVILY_API_KEY")
    request_timeout_seconds: float = Field(default=30.0, alias="REQUEST_TIMEOUT_SECONDS")
    max_search_queries: int = Field(default=3, alias="MAX_SEARCH_QUERIES")
    max_sources: int = Field(default=5, alias="MAX_SOURCES")

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def parse_frontend_origins(cls, value: Any) -> List[str]:
        """Support JSON string, comma-separated string, or native list."""
        if isinstance(value, str):
            val_str = value.strip()
            if val_str.startswith("[") and val_str.endswith("]"):
                try:
                    parsed = json.loads(val_str)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in val_str.split(",") if origin.strip()]
        if isinstance(value, (list, tuple)):
            return [str(item).strip() for item in value if str(item).strip()]
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("max_sources")
    @classmethod
    def validate_max_sources_range(cls, value: int) -> int:
        if value < 1 or value > 20:
            raise ValueError("MAX_SOURCES must be between 1 and 20.")
        return value

    @field_validator("max_search_queries")
    @classmethod
    def validate_max_queries_range(cls, value: int) -> int:
        if value < 1 or value > 10:
            raise ValueError("MAX_SEARCH_QUERIES must be between 1 and 10.")
        return value

    def is_llm_configured(self) -> bool:
        """Check if the currently active LLM provider has an API key."""
        provider = self.llm_provider.lower().strip()
        if provider == "openai":
            return bool(self.openai_api_key and self.openai_api_key.strip())
        elif provider == "groq":
            return bool(self.groq_api_key and self.groq_api_key.strip())
        elif provider == "anthropic":
            return bool(self.anthropic_api_key and self.anthropic_api_key.strip())
        elif provider == "gemini":
            return bool(self.gemini_api_key and self.gemini_api_key.strip())
        return False

    def is_tavily_configured(self) -> bool:
        """Check if Tavily search API key is configured."""
        return bool(self.tavily_api_key and self.tavily_api_key.strip())

    def validate_llm_credentials(self) -> None:
        """Validate that credentials for active LLM provider are available."""
        if not self.is_llm_configured():
            raise ValueError(
                f"LLM provider '{self.llm_provider}' requires an API key, but none is configured. "
                f"Please set {self.llm_provider.upper()}_API_KEY."
            )

    def validate_tavily_credentials(self) -> None:
        """Validate that Tavily credentials are available."""
        if not self.is_tavily_configured():
            raise ValueError(
                "Tavily search requires an API key, but TAVILY_API_KEY is not configured."
            )

    def safe_dict(self) -> dict:
        """Return non-sensitive configuration parameters safely."""
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "environment": self.environment,
            "log_level": self.log_level,
            "frontend_origins": self.frontend_origins,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "gemini_base_url": self.gemini_base_url,
            "is_llm_configured": self.is_llm_configured(),
            "is_tavily_configured": self.is_tavily_configured(),
            "request_timeout_seconds": self.request_timeout_seconds,
            "max_search_queries": self.max_search_queries,
            "max_sources": self.max_sources,
        }

    def __repr__(self) -> str:
        return f"<Settings app='{self.app_name}' env='{self.environment}' provider='{self.llm_provider}'>"

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
