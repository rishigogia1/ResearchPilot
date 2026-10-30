import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import openai
from app.services.llm_service import (
    LLMAuthenticationError,
    LLMCredentialsError,
    LLMMalformedResponseError,
    LLMNotFoundError,
    LLMPermissionError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMService,
    extract_json_from_text,
    sanitize_error_message,
)


@pytest.mark.asyncio
async def test_llm_service_missing_credentials(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_provider", "openai")

    svc = LLMService(provider="openai")
    with pytest.raises(LLMCredentialsError) as exc:
        await svc.generate_chat([{"role": "user", "content": "Hello"}])
    assert "OpenAI API key is missing" in str(exc.value)


@pytest.mark.asyncio
async def test_gemini_missing_credentials(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "gemini_api_key", None)
    monkeypatch.setattr(settings, "llm_provider", "gemini")

    svc = LLMService(provider="gemini")
    with pytest.raises(LLMCredentialsError) as exc:
        await svc.generate_chat([{"role": "user", "content": "Hello"}])
    assert "Gemini API key is missing" in str(exc.value)


def test_gemini_client_configuration(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "gemini_api_key", "AQ.dummy-test-key-for-gemini-client")
    monkeypatch.setattr(settings, "gemini_base_url", "https://generativelanguage.googleapis.com/v1beta/openai/")
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_model", "gemini-3.8-flash")

    svc = LLMService(provider="gemini", model="gemini-3.8-flash")
    client = svc._get_client()

    assert str(client.base_url).startswith("https://generativelanguage.googleapis.com/v1beta/openai")
    assert client.api_key == "AQ.dummy-test-key-for-gemini-client"
    assert svc.model == "gemini-3.8-flash"


@pytest.mark.asyncio
async def test_llm_service_unsupported_provider():
    svc = LLMService(provider="unsupported_dummy_provider")
    with pytest.raises(Exception) as exc:
        await svc.generate_chat([{"role": "user", "content": "Hello"}])
    assert "not supported" in str(exc.value)


@pytest.mark.asyncio
async def test_llm_service_auth_failure_sanitized(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "openai_api_key", "sk-invalid-dummy-key")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.AuthenticationError(
            message="Incorrect API key provided: sk-invalid-dummy-key",
            response=MagicMock(status_code=401),
            body={},
        )
    )

    svc = LLMService(provider="openai")
    with patch.object(svc, "_get_openai_client", return_value=mock_client):
        with pytest.raises(LLMAuthenticationError) as exc:
            await svc.generate_chat([{"role": "user", "content": "Hello"}])
        assert "sk-invalid-dummy-key" not in str(exc.value)


@pytest.mark.asyncio
async def test_gemini_auth_failure_401(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "gemini_api_key", "AQ.invalid-key-secret-1234")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.AuthenticationError(
            message="API key not valid. Pass a valid key: AQ.invalid-key-secret-1234",
            response=MagicMock(status_code=401),
            body={},
        )
    )

    svc = LLMService(provider="gemini", model="gemini-3.8-flash")
    with patch.object(svc, "_get_openai_client", return_value=mock_client):
        with pytest.raises(LLMAuthenticationError) as exc:
            await svc.generate_chat([{"role": "user", "content": "Hello"}])
        assert "AQ.invalid-key-secret-1234" not in str(exc.value)
        assert "401" in str(exc.value)


@pytest.mark.asyncio
async def test_gemini_permission_denied_403(monkeypatch):
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.PermissionDeniedError(
            message="Project or account restriction",
            response=MagicMock(status_code=403),
            body={},
        )
    )

    svc = LLMService(provider="gemini", model="gemini-3.8-flash")
    with patch.object(svc, "_get_openai_client", return_value=mock_client):
        with pytest.raises(LLMPermissionError) as exc:
            await svc.generate_chat([{"role": "user", "content": "Hello"}])
        assert exc.value.code == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_gemini_model_not_found_404(monkeypatch):
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.NotFoundError(
            message="Model not found: models/gemini-nonexistent",
            response=MagicMock(status_code=404),
            body={},
        )
    )

    svc = LLMService(provider="gemini", model="models/gemini-nonexistent")
    with patch.object(svc, "_get_openai_client", return_value=mock_client):
        with pytest.raises(LLMNotFoundError) as exc:
            await svc.generate_chat([{"role": "user", "content": "Hello"}])
        assert exc.value.code == "MODEL_NOT_FOUND"


@pytest.mark.asyncio
async def test_gemini_rate_limit_429(monkeypatch):
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.RateLimitError(
            message="Resource exhausted: quota exceeded",
            response=MagicMock(status_code=429),
            body={},
        )
    )

    svc = LLMService(provider="gemini", max_retries=1)
    with patch.object(svc, "_get_openai_client", return_value=mock_client):
        with pytest.raises(LLMRateLimitError) as exc:
            await svc.generate_chat([{"role": "user", "content": "Hello"}])
        assert exc.value.code == "RATE_LIMITED"
    assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_gemini_provider_unavailable_5xx(monkeypatch):
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.InternalServerError(
            message="The service is temporarily overloaded",
            response=MagicMock(status_code=503),
            body={},
        )
    )

    svc = LLMService(provider="gemini", max_retries=1)
    with patch.object(svc, "_get_openai_client", return_value=mock_client):
        with pytest.raises(LLMProviderUnavailableError) as exc:
            await svc.generate_chat([{"role": "user", "content": "Hello"}])
        assert exc.value.code == "PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_llm_service_input_truncation():
    svc = LLMService()
    huge_text = "word " * 15000  # ~75,000 chars
    messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": huge_text},
    ]
    truncated = svc._truncate_messages(messages, max_chars=1000)
    total_len = sum(len(m["content"]) for m in truncated)
    assert total_len < len(huge_text)
    assert "[truncated for length]" in truncated[1]["content"]


@pytest.mark.asyncio
async def test_llm_service_generate_json_success():
    mock_choice = MagicMock()
    mock_choice.message.content = '{"analysis": "success", "confidence": 0.95}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 25
    mock_response.usage.completion_tokens = 15
    mock_response.usage.total_tokens = 40

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    svc = LLMService(provider="gemini", model="gemini-3.8-flash")
    with patch.object(svc, "_get_openai_client", return_value=mock_client):
        res = await svc.generate_json([{"role": "user", "content": "Give JSON"}])
        assert res.parsed_json == {"analysis": "success", "confidence": 0.95}
        assert res.usage.total_tokens == 40
        assert res.latency_ms >= 0


@pytest.mark.asyncio
async def test_gemini_structured_json_with_markdown_fences():
    mock_choice = MagicMock()
    mock_choice.message.content = '```json\n{\n  "objective": "Compare Milvus and Qdrant",\n  "queries": ["milvus scale", "qdrant scale"]\n}\n```'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = None

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    svc = LLMService(provider="gemini", model="gemini-3.8-flash")
    with patch.object(svc, "_get_openai_client", return_value=mock_client):
        res = await svc.generate_json([{"role": "user", "content": "Give JSON"}])
        assert res.parsed_json == {
            "objective": "Compare Milvus and Qdrant",
            "queries": ["milvus scale", "qdrant scale"],
        }


@pytest.mark.asyncio
async def test_gemini_malformed_json_raises():
    mock_choice = MagicMock()
    mock_choice.message.content = 'This is plain text with no json whatsoever.'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = None

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    svc = LLMService(provider="gemini", max_retries=1)
    with patch.object(svc, "_get_openai_client", return_value=mock_client):
        with pytest.raises(LLMMalformedResponseError):
            await svc.generate_json([{"role": "user", "content": "Give JSON"}])


def test_sanitize_error_message():
    raw_error = "Failed to connect with key sk-abcdef1234567890abcdef and Gemini key AQ.1234567890abcdef1234567890"
    sanitized = sanitize_error_message(raw_error)
    assert "sk-abcdef" not in sanitized
    assert "AQ.123456" not in sanitized
    assert "[REDACTED_OPENAI_KEY]" in sanitized
    assert "[REDACTED_GEMINI_KEY]" in sanitized


def test_extract_json_from_text_variants():
    # Direct JSON
    assert extract_json_from_text('{"a": 1}') == {"a": 1}

    # Markdown fence
    assert extract_json_from_text('```json\n{"b": 2}\n```') == {"b": 2}

    # Surrounding conversational chatter
    assert extract_json_from_text('Sure, here is the result: {"c": 3}\nHope this helps!') == {"c": 3}

    # Invalid JSON raises JSONDecodeError
    with pytest.raises(Exception):
        extract_json_from_text('No json here!')
