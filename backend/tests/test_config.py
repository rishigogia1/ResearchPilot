import pytest
from app.config import Settings


def test_config_defaults():
    settings = Settings()
    assert settings.app_name == "ResearchPilot API"
    assert settings.llm_provider in ("openai", "groq", "anthropic", "gemini")
    assert settings.request_timeout_seconds > 0
    assert settings.max_sources >= 1
    assert settings.max_search_queries >= 1


def test_frontend_origins_parsing():
    # Comma-separated string
    s1 = Settings(FRONTEND_ORIGINS="http://localhost:5173, https://app.example.com")
    assert s1.frontend_origins == ["http://localhost:5173", "https://app.example.com"]

    # JSON array string
    s2 = Settings(FRONTEND_ORIGINS='["http://localhost:3000", "http://127.0.0.1:3000"]')
    assert s2.frontend_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Native list
    s3 = Settings(FRONTEND_ORIGINS=["http://test.com"])
    assert s3.frontend_origins == ["http://test.com"]


def test_safe_dict_never_exposes_secrets():
    s = Settings(
        OPENAI_API_KEY="sk-super-secret-key-12345",
        TAVILY_API_KEY="tvly-super-secret-key-67890",
    )
    safe = s.safe_dict()
    # Confirm secrets are not present in keys or values
    assert "openai_api_key" not in safe
    assert "tavily_api_key" not in safe
    for k, v in safe.items():
        assert "sk-super-secret" not in str(v)
        assert "tvly-super-secret" not in str(v)


def test_validate_credentials_raises_when_missing():
    s = Settings(LLM_PROVIDER="openai", OPENAI_API_KEY=None, TAVILY_API_KEY=None)
    with pytest.raises(ValueError) as exc_llm:
        s.validate_llm_credentials()
    assert "OPENAI_API_KEY" in str(exc_llm.value)

    s_gemini = Settings(LLM_PROVIDER="gemini", GEMINI_API_KEY=None, TAVILY_API_KEY=None)
    with pytest.raises(ValueError) as exc_gem:
        s_gemini.validate_llm_credentials()
    assert "GEMINI_API_KEY" in str(exc_gem.value)

    with pytest.raises(ValueError) as exc_tavily:
        s.validate_tavily_credentials()
    assert "TAVILY_API_KEY" in str(exc_tavily.value)


def test_validate_credentials_succeeds_when_present():
    s_openai = Settings(
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-valid-mock-key",
        TAVILY_API_KEY="tvly-valid-mock-key",
    )
    s_openai.validate_llm_credentials()
    s_openai.validate_tavily_credentials()

    s_gemini = Settings(
        LLM_PROVIDER="gemini",
        GEMINI_API_KEY="AQ.valid-gemini-mock-key",
        TAVILY_API_KEY="tvly-valid-mock-key",
    )
    s_gemini.validate_llm_credentials()
    s_gemini.validate_tavily_credentials()


def test_gemini_config_defaults():
    s = Settings()
    assert s.gemini_base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"
    safe = s.safe_dict()
    assert "gemini_base_url" in safe
    assert safe["gemini_base_url"] == "https://generativelanguage.googleapis.com/v1beta/openai/"
