import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

import openai
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger("researchpilot.services.llm")


# ==============================================================================
# Sensitive Information Sanitization
# ==============================================================================

def sanitize_error_message(msg: str) -> str:
    """
    Remove API keys and sensitive tokens from error strings and log messages.
    Ensures that external provider error payloads do not expose credentials.
    """
    if not msg:
        return ""
    sanitized = str(msg)
    # Redact OpenAI keys
    sanitized = re.sub(r"sk-[a-zA-Z0-9_\-]{16,}", "[REDACTED_OPENAI_KEY]", sanitized)
    # Redact Google/Gemini keys
    sanitized = re.sub(r"AQ\.[a-zA-Z0-9_\-]{20,}", "[REDACTED_GEMINI_KEY]", sanitized)
    sanitized = re.sub(r"AIza[a-zA-Z0-9_\-]{20,}", "[REDACTED_GEMINI_KEY]", sanitized)
    # Redact Tavily keys
    sanitized = re.sub(r"tvly-[a-zA-Z0-9_\-]{16,}", "[REDACTED_TAVILY_KEY]", sanitized)
    # Explicitly replace active environment secrets if present in message
    if getattr(settings, "gemini_api_key", None):
        sanitized = sanitized.replace(settings.gemini_api_key, "[REDACTED_GEMINI_KEY]")
    if getattr(settings, "openai_api_key", None):
        sanitized = sanitized.replace(settings.openai_api_key, "[REDACTED_OPENAI_KEY]")
    if getattr(settings, "tavily_api_key", None):
        sanitized = sanitized.replace(settings.tavily_api_key, "[REDACTED_TAVILY_KEY]")
    return sanitized


def extract_json_from_text(content: str) -> Dict[str, Any]:
    """
    Robustly extract and decode a JSON object from model output.
    Handles raw JSON, markdown-wrapped blocks (```json ... ```),
    and JSON strings embedded in surrounding model chatter.
    Preserves strict JSON syntax validation without bypassing Pydantic models.
    """
    raw = content.strip()

    # 1. Direct parse attempt
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 2. Extract from markdown code fences (```json ... ``` or ``` ... ```)
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if code_block_match:
        block_content = code_block_match.group(1).strip()
        try:
            parsed = json.loads(block_content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # 3. Extract outermost balanced curly braces
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        snippet = raw[first_brace : last_brace + 1].strip()
        try:
            parsed = json.loads(snippet)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("Could not extract a valid JSON object from LLM response content.", raw, 0)


# ==============================================================================
# Exceptions
# ==============================================================================

class LLMServiceError(Exception):
    """Base exception for LLM operations."""
    def __init__(self, message: str, code: str = "LLM_ERROR"):
        super().__init__(message)
        self.code = code
        self.message = message


class LLMCredentialsError(LLMServiceError):
    """Raised when API credentials are missing or unconfigured."""
    def __init__(self, message: str):
        super().__init__(message, code="MISSING_CREDENTIALS")


class LLMAuthenticationError(LLMServiceError):
    """Raised when provider returns HTTP 401 (invalid API key)."""
    def __init__(self, message: str = "LLM authentication failed. Please verify API key."):
        super().__init__(message, code="AUTH_FAILURE")


class LLMPermissionError(LLMServiceError):
    """Raised when provider returns HTTP 403 (permission or project restriction)."""
    def __init__(self, message: str = "LLM permission denied or project restriction (HTTP 403)."):
        super().__init__(message, code="PERMISSION_DENIED")


class LLMNotFoundError(LLMServiceError):
    """Raised when provider returns HTTP 404 (model not found)."""
    def __init__(self, message: str = "LLM model not found (HTTP 404)."):
        super().__init__(message, code="MODEL_NOT_FOUND")


class LLMRateLimitError(LLMServiceError):
    """Raised when provider returns HTTP 429 (rate limit or quota exceeded)."""
    def __init__(self, message: str = "LLM rate limit or quota exceeded. Please check provider limits or retry later."):
        super().__init__(message, code="RATE_LIMITED")


class LLMProviderUnavailableError(LLMServiceError):
    """Raised when provider returns HTTP 5xx (service unavailable)."""
    def __init__(self, message: str = "LLM provider service unavailable (HTTP 5xx). Please retry later."):
        super().__init__(message, code="PROVIDER_UNAVAILABLE")


class LLMTimeoutError(LLMServiceError):
    """Raised when LLM request times out."""
    def __init__(self, message: str = "LLM generation request timed out."):
        super().__init__(message, code="TIMEOUT")


class LLMMalformedResponseError(LLMServiceError):
    """Raised when response cannot be parsed or validated as JSON."""
    def __init__(self, message: str = "LLM returned a malformed response."):
        super().__init__(message, code="MALFORMED_RESPONSE")


# ==============================================================================
# LLM Response Model
# ==============================================================================

class LLMUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    content: str
    parsed_json: Optional[Dict[str, Any]] = None
    provider: str
    model: str
    latency_ms: float
    usage: LLMUsage = Field(default_factory=LLMUsage)


# ==============================================================================
# LLM Service Implementation
# ==============================================================================

class LLMService:
    """
    LLM abstraction service layer.
    Supports Google Gemini (via OpenAI-compatible endpoint) and OpenAI API
    with bounded retries, structured JSON outputs, sanitized error logging,
    latency tracking, and token usage metrics.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 2,
        timeout_seconds: Optional[float] = None,
    ):
        self.provider = (provider or settings.llm_provider).lower().strip()
        self.model = model or settings.llm_model
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds or settings.request_timeout_seconds

    def _get_client(self) -> AsyncOpenAI:
        """Initialize AsyncOpenAI client configured for the active LLM provider."""
        return self._get_openai_client()

    def _get_openai_client(self) -> AsyncOpenAI:
        """
        Initialize AsyncOpenAI client configured for the active LLM provider.
        Supports:
          - "gemini": Google Gemini OpenAI-compatible endpoint
          - "openai": Standard OpenAI endpoint
        """
        if self.provider == "gemini":
            api_key = settings.gemini_api_key
            if not api_key or not api_key.strip():
                raise LLMCredentialsError(
                    "Gemini API key is missing. Please configure GEMINI_API_KEY in backend/.env."
                )
            base_url = settings.gemini_base_url
            return AsyncOpenAI(
                api_key=api_key.strip(),
                base_url=base_url,
                timeout=self.timeout_seconds,
                max_retries=0,  # We manage retries explicitly with backoff
            )

        elif self.provider == "openai":
            api_key = settings.openai_api_key
            if not api_key or not api_key.strip():
                raise LLMCredentialsError(
                    "OpenAI API key is missing. Please configure OPENAI_API_KEY in backend/.env."
                )
            return AsyncOpenAI(
                api_key=api_key.strip(),
                timeout=self.timeout_seconds,
                max_retries=0,
            )

        raise LLMServiceError(
            f"Configured LLM provider '{self.provider}' is not supported in this runtime. Supported providers: 'gemini', 'openai'.",
            code="UNSUPPORTED_PROVIDER",
        )

    def _truncate_messages(self, messages: List[Dict[str, str]], max_chars: int = 40000) -> List[Dict[str, str]]:
        """Safeguard against unbounded input context length."""
        total_len = sum(len(m.get("content", "")) for m in messages)
        if total_len <= max_chars:
            return messages

        truncated_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if len(content) > max_chars // 2 and msg.get("role") != "system":
                content = content[: max_chars // 2] + "\n...[truncated for length]"
            truncated_messages.append({"role": msg["role"], "content": content})
        return truncated_messages

    def _classify_and_handle_error(self, exc: Exception, attempt: int) -> bool:
        """
        Map upstream API exceptions to classified errors.
        Returns True if the error is transient and should be retried.
        Raises the classified exception immediately if non-retryable.
        """
        status_code = getattr(exc, "status_code", None)
        sanitized_msg = sanitize_error_message(str(exc))

        # 401 Unauthorized: Invalid API key (non-retryable)
        if isinstance(exc, openai.AuthenticationError) or status_code == 401:
            logger.error(
                "LLM authentication failure (HTTP 401) on provider '%s': %s",
                self.provider,
                sanitized_msg,
            )
            raise LLMAuthenticationError(
                f"Invalid API key for {self.provider.capitalize()} (HTTP 401). Please check credentials."
            ) from None

        # 403 Forbidden: Permission or project restriction (non-retryable)
        if isinstance(exc, openai.PermissionDeniedError) or status_code == 403:
            logger.error(
                "LLM permission denied (HTTP 403) on provider '%s': %s",
                self.provider,
                sanitized_msg,
            )
            raise LLMPermissionError(
                f"Permission or project restriction for {self.provider.capitalize()} (HTTP 403)."
            ) from None

        # 404 Not Found: Model not found (non-retryable)
        if isinstance(exc, openai.NotFoundError) or status_code == 404:
            logger.error(
                "LLM model not found (HTTP 404) on provider '%s' (model='%s'): %s",
                self.provider,
                self.model,
                sanitized_msg,
            )
            raise LLMNotFoundError(
                f"Model '{self.model}' not found on {self.provider.capitalize()} (HTTP 404)."
            ) from None

        # 429 Rate Limit / Quota Exceeded (retryable)
        if isinstance(exc, openai.RateLimitError) or status_code == 429:
            logger.warning(
                "LLM rate limit reached (HTTP 429) on attempt %d/%d for provider '%s': %s",
                attempt,
                self.max_retries + 1,
                self.provider,
                sanitized_msg,
            )
            return True

        # 5xx Server Errors (retryable)
        if isinstance(exc, openai.InternalServerError) or (status_code and 500 <= status_code < 600):
            logger.warning(
                "LLM provider server error (HTTP %s) on attempt %d/%d for provider '%s': %s",
                status_code or "5xx",
                attempt,
                self.max_retries + 1,
                self.provider,
                sanitized_msg,
            )
            return True

        # Timeout & Connection Errors (retryable)
        if isinstance(exc, (openai.APITimeoutError, openai.APIConnectionError)):
            logger.warning(
                "LLM connection/timeout error (%s) on attempt %d/%d for provider '%s': %s",
                type(exc).__name__,
                attempt,
                self.max_retries + 1,
                self.provider,
                sanitized_msg,
            )
            return True

        # Unknown / unhandled exceptions
        logger.error(
            "LLM unhandled failure (%s) on provider '%s': %s",
            type(exc).__name__,
            self.provider,
            sanitized_msg,
        )
        raise LLMServiceError(
            f"LLM request failed: {type(exc).__name__}: {sanitized_msg}"
        ) from None

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Generate conversational chat response with bounded retries."""
        client = self._get_client()
        bounded_messages = self._truncate_messages(messages)

        start_time = time.perf_counter()
        attempt = 0
        last_error: Optional[Exception] = None

        while attempt <= self.max_retries:
            attempt += 1
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=bounded_messages,  # type: ignore
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                choice = response.choices[0]
                content = choice.message.content or ""

                usage = LLMUsage()
                if response.usage:
                    usage = LLMUsage(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    )

                logger.info(
                    "LLM generate_chat success: provider=%s model=%s tokens=%d latency=%.2fms",
                    self.provider,
                    self.model,
                    usage.total_tokens,
                    latency_ms,
                )
                return LLMResponse(
                    content=content,
                    provider=self.provider,
                    model=self.model,
                    latency_ms=latency_ms,
                    usage=usage,
                )

            except Exception as e:
                last_error = e
                should_retry = self._classify_and_handle_error(e, attempt)
                if should_retry and attempt <= self.max_retries:
                    backoff = (2 ** (attempt - 1)) * 0.5
                    await asyncio.sleep(backoff)
                elif not should_retry:
                    raise

        # If loop ended after retryable errors exhausted
        self._raise_final_retry_error(last_error)

    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 3000,
    ) -> LLMResponse:
        """
        Generate structured JSON output with validated JSON object format.
        Uses extract_json_from_text to safely parse outputs even if models
        wrap JSON in markdown code blocks or additional text.
        """
        client = self._get_client()
        bounded_messages = self._truncate_messages(messages)

        start_time = time.perf_counter()
        attempt = 0
        last_error: Optional[Exception] = None

        while attempt <= self.max_retries:
            attempt += 1
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=bounded_messages,  # type: ignore
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                content = response.choices[0].message.content or "{}"

                try:
                    parsed = extract_json_from_text(content)
                except json.JSONDecodeError as json_err:
                    logger.warning(
                        "LLM response was not valid JSON on attempt %d: %s",
                        attempt,
                        str(json_err),
                    )
                    if attempt <= self.max_retries:
                        await asyncio.sleep(0.5)
                        continue
                    raise LLMMalformedResponseError("LLM response could not be parsed as JSON.")

                usage = LLMUsage()
                if response.usage:
                    usage = LLMUsage(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    )

                logger.info(
                    "LLM generate_json success: provider=%s model=%s tokens=%d latency=%.2fms",
                    self.provider,
                    self.model,
                    usage.total_tokens,
                    latency_ms,
                )
                return LLMResponse(
                    content=content,
                    parsed_json=parsed,
                    provider=self.provider,
                    model=self.model,
                    latency_ms=latency_ms,
                    usage=usage,
                )

            except (LLMServiceError, LLMMalformedResponseError):
                raise

            except Exception as e:
                last_error = e
                should_retry = self._classify_and_handle_error(e, attempt)
                if should_retry and attempt <= self.max_retries:
                    backoff = (2 ** (attempt - 1)) * 0.5
                    await asyncio.sleep(backoff)
                elif not should_retry:
                    raise

        self._raise_final_retry_error(last_error)

    def _raise_final_retry_error(self, last_error: Optional[Exception]) -> None:
        """Raise appropriate exception after retries are exhausted."""
        status_code = getattr(last_error, "status_code", None)
        if isinstance(last_error, openai.RateLimitError) or status_code == 429:
            raise LLMRateLimitError(
                f"{self.provider.capitalize()} rate limit or quota exceeded (HTTP 429)."
            )
        elif isinstance(last_error, openai.APITimeoutError):
            raise LLMTimeoutError(
                f"{self.provider.capitalize()} request timed out after {self.max_retries + 1} attempts."
            )
        elif isinstance(last_error, openai.InternalServerError) or (status_code and 500 <= status_code < 600):
            raise LLMProviderUnavailableError(
                f"{self.provider.capitalize()} service unavailable (HTTP {status_code or '5xx'})."
            )
        elif isinstance(last_error, openai.APIConnectionError):
            raise LLMProviderUnavailableError(
                f"Failed to connect to {self.provider.capitalize()} service."
            )
        else:
            raise LLMServiceError(
                f"LLM request failed after {self.max_retries + 1} attempts: {type(last_error).__name__}"
            )


# Default singleton instance
llm_service = LLMService()
