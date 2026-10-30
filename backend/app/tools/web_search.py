import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from pydantic import BaseModel, Field

from tavily import AsyncTavilyClient, InvalidAPIKeyError, UsageLimitExceededError
from app.config import settings

logger = logging.getLogger("researchpilot.tools.search")


# ==============================================================================
# Exceptions
# ==============================================================================

class SearchToolError(Exception):
    """Base exception for search tool operations."""
    def __init__(self, message: str, code: str = "SEARCH_ERROR"):
        super().__init__(message)
        self.code = code
        self.message = message


class TavilyCredentialsError(SearchToolError):
    """Raised when Tavily API key is missing."""
    def __init__(self, message: str = "Tavily API key is missing. Please set TAVILY_API_KEY in backend/.env."):
        super().__init__(message, code="MISSING_CREDENTIALS")


class TavilyAuthError(SearchToolError):
    """Raised when Tavily rejects API key."""
    def __init__(self, message: str = "Tavily authentication failed. Please verify TAVILY_API_KEY."):
        super().__init__(message, code="AUTH_FAILURE")


class TavilyRateLimitError(SearchToolError):
    """Raised when Tavily quota or rate limit is exceeded."""
    def __init__(self, message: str = "Tavily rate or usage limit exceeded."):
        super().__init__(message, code="RATE_LIMITED")


class TavilyTimeoutError(SearchToolError):
    """Raised when search request times out."""
    def __init__(self, message: str = "Tavily search request timed out."):
        super().__init__(message, code="TIMEOUT")


# ==============================================================================
# Data Models
# ==============================================================================

class SearchResultItem(BaseModel):
    """Individual parsed and validated search result item."""
    title: str
    url: str
    snippet: str
    domain: str
    published_date: Optional[str] = None
    score: Optional[float] = None


class SearchResponse(BaseModel):
    """Normalized search response bundle."""
    query: str
    results: List[SearchResultItem] = Field(default_factory=list)
    total_results: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None


# ==============================================================================
# URL Helpers
# ==============================================================================

def normalize_url(raw_url: str) -> Optional[str]:
    """Clean and normalize URL; remove tracking parameters and fragments."""
    if not raw_url or not isinstance(raw_url, str):
        return None
    cleaned = raw_url.strip()
    try:
        parsed = urlparse(cleaned)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return None

        # Filter out common tracking query params
        filtered_query = [
            (k, v) for k, v in parse_qsl(parsed.query)
            if not k.lower().startswith("utm_") and k.lower() not in ("gclid", "fbclid", "ref")
        ]
        new_query = urlencode(filtered_query)

        # Normalize path
        normalized_path = parsed.path.rstrip("/") if parsed.path != "/" else "/"

        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            parsed.params,
            new_query,
            "",  # Strip fragment
        ))
        return normalized
    except Exception:
        return None


# ==============================================================================
# Search Tool Implementation
# ==============================================================================

class TavilySearchTool:
    """
    Tavily search engine wrapper.
    Executes live web searches with bounded concurrency, retry on transient failures,
    URL sanitization, and deduplication.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_retries: int = 2,
        timeout_seconds: Optional[float] = None,
    ):
        self._api_key = api_key
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds or settings.request_timeout_seconds

    def _get_api_key(self) -> str:
        key = self._api_key or settings.tavily_api_key
        if not key or not key.strip():
            raise TavilyCredentialsError()
        return key.strip()

    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
    ) -> SearchResponse:
        """
        Execute web search query against Tavily.
        Enforces bounded results, deduplication, and safe error handling.
        """
        api_key = self._get_api_key()
        cleaned_query = query.strip()
        if not cleaned_query:
            return SearchResponse(query=query, results=[], total_results=0, latency_ms=0.0)

        bounded_limit = max(1, min(max_results, settings.max_sources, 10))
        start_time = time.perf_counter()

        client = AsyncTavilyClient(api_key=api_key)
        attempt = 0
        last_error: Optional[Exception] = None

        while attempt <= self.max_retries:
            attempt += 1
            try:
                raw_response = await asyncio.wait_for(
                    client.search(
                        query=cleaned_query,
                        max_results=bounded_limit,
                        search_depth=search_depth,
                    ),
                    timeout=self.timeout_seconds,
                )

                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                raw_results = raw_response.get("results", []) if isinstance(raw_response, dict) else []

                # Deduplicate and validate
                seen_urls = set()
                deduped_results: List[SearchResultItem] = []

                for r in raw_results:
                    if not isinstance(r, dict):
                        continue
                    url = normalize_url(r.get("url", ""))
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc

                    title = (r.get("title") or domain).strip()
                    snippet = (r.get("content") or "").strip()
                    published_date = r.get("published_date")
                    score = r.get("score")

                    deduped_results.append(
                        SearchResultItem(
                            title=title,
                            url=url,
                            snippet=snippet,
                            domain=domain,
                            published_date=str(published_date) if published_date else None,
                            score=float(score) if score is not None else None,
                        )
                    )

                logger.info(
                    "Tavily search success: query='%s' raw=%d deduped=%d latency=%.2fms",
                    cleaned_query,
                    len(raw_results),
                    len(deduped_results),
                    latency_ms,
                )

                return SearchResponse(
                    query=cleaned_query,
                    results=deduped_results,
                    total_results=len(deduped_results),
                    latency_ms=latency_ms,
                )

            except InvalidAPIKeyError:
                logger.error("Tavily authentication failure")
                raise TavilyAuthError() from None

            except UsageLimitExceededError:
                logger.error("Tavily quota or usage limit exceeded")
                raise TavilyRateLimitError() from None

            except asyncio.TimeoutError:
                last_error = TavilyTimeoutError()
                logger.warning("Tavily search timeout on attempt %d for query: '%s'", attempt, cleaned_query)
                if attempt <= self.max_retries:
                    await asyncio.sleep(0.5 * attempt)
                else:
                    break

            except Exception as e:
                last_error = e
                logger.warning("Tavily search attempt %d error: %s", attempt, str(e))
                if attempt <= self.max_retries:
                    await asyncio.sleep(0.5 * attempt)
                else:
                    break

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        if isinstance(last_error, SearchToolError):
            raise last_error
        raise SearchToolError(f"Tavily search failed for query '{cleaned_query}': {type(last_error).__name__}")


tavily_search_tool = TavilySearchTool()
