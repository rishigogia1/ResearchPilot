import asyncio
from datetime import datetime, timezone
import ipaddress
import logging
import re
import socket
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import httpx
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger("researchpilot.tools.reader")


# ==============================================================================
# Exceptions
# ==============================================================================

class ExtractionError(Exception):
    """Base exception for page extraction."""
    pass


class SSRFSecurityError(ExtractionError):
    """Raised when URL attempts to access private, local, or prohibited network destinations."""
    pass


# ==============================================================================
# Models
# ==============================================================================

class ExtractedPage(BaseModel):
    """Cleaned webpage textual extract with metadata."""
    url: str
    final_url: str
    title: str
    content: str
    content_length: int
    http_status: int
    content_type: str
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_truncated: bool = False
    error: Optional[str] = None


# ==============================================================================
# SSRF Protection Validator
# ==============================================================================

PROHIBITED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}


def is_prohibited_ip(ip_str: str) -> bool:
    """Check if an IP string is private, loopback, link-local, multicast, or cloud metadata."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_link_local
            or ip.is_unspecified
        ):
            return True
        # Explicit check for AWS / Azure / GCP metadata IP 169.254.169.254
        if ip_str == "169.254.169.254":
            return True
        return False
    except ValueError:
        return True


async def validate_url_safety(url: str) -> None:
    """
    Validate that target URL does not resolve to private networks or localhost.
    Rejects disallowed schemes and non-routable IPs.
    """
    if not url or not isinstance(url, str):
        raise SSRFSecurityError("URL cannot be empty.")

    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise SSRFSecurityError(f"Prohibited URL scheme '{parsed.scheme}'. Only http and https are allowed.")

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise SSRFSecurityError("URL must contain a valid hostname.")

    if hostname in PROHIBITED_HOSTNAMES or hostname.endswith(".local") or hostname.endswith(".internal"):
        raise SSRFSecurityError(f"Access to local or private hostname '{hostname}' is blocked for security.")

    # Check if hostname itself is an IP literal
    try:
        if is_prohibited_ip(hostname):
            raise SSRFSecurityError(f"Access to private or reserved IP '{hostname}' is blocked.")
    except Exception:
        pass

    # Resolve DNS asynchronously to verify all resolved IP addresses
    loop = asyncio.get_running_loop()
    try:
        addr_info = await loop.run_in_executor(
            None,
            socket.getaddrinfo,
            hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        )
    except socket.gaierror as e:
        raise SSRFSecurityError(f"DNS resolution failed for hostname '{hostname}': {str(e)}")

    for family, _, _, _, sockaddr in addr_info:
        ip_addr = sockaddr[0]
        if is_prohibited_ip(ip_addr):
            raise SSRFSecurityError(
                f"Hostname '{hostname}' resolved to prohibited or private IP '{ip_addr}'."
            )


# ==============================================================================
# Webpage Reader
# ==============================================================================

class WebpageReader:
    """
    Resilient webpage content reader using HTTPX and BeautifulSoup.
    Implements strict SSRF protection, redirect verification, text cleaning,
    and length enforcement.
    """

    ALLOWED_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
    MAX_CONTENT_CHARS = 6000
    MAX_REDIRECTS = 3

    def __init__(
        self,
        timeout_seconds: float = 8.0,
        max_concurrency: int = 4,
    ):
        self.timeout_seconds = timeout_seconds
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def fetch_page(self, url: str) -> ExtractedPage:
        """Fetch and extract single webpage with SSRF revalidation on redirects."""
        async with self.semaphore:
            current_url = url
            redirect_count = 0

            async with httpx.AsyncClient(
                headers=self.headers,
                timeout=self.timeout_seconds,
                follow_redirects=False,  # Manually re-validate redirects against SSRF
            ) as client:
                while redirect_count <= self.MAX_REDIRECTS:
                    # 1. Validate safety of target URL before network request
                    try:
                        await validate_url_safety(current_url)
                    except SSRFSecurityError as ssrf_err:
                        logger.warning("SSRF blocked URL '%s': %s", current_url, str(ssrf_err))
                        return ExtractedPage(
                            url=url,
                            final_url=current_url,
                            title="",
                            content="",
                            content_length=0,
                            http_status=403,
                            content_type="",
                            error=f"SSRF_BLOCKED: {str(ssrf_err)}",
                        )

                    # 2. Perform GET request
                    try:
                        resp = await client.get(current_url)
                    except (httpx.TimeoutException, asyncio.TimeoutError):
                        return ExtractedPage(
                            url=url,
                            final_url=current_url,
                            title="",
                            content="",
                            content_length=0,
                            http_status=408,
                            content_type="",
                            error="HTTP_TIMEOUT",
                        )
                    except Exception as net_err:
                        return ExtractedPage(
                            url=url,
                            final_url=current_url,
                            title="",
                            content="",
                            content_length=0,
                            http_status=500,
                            content_type="",
                            error=f"NETWORK_ERROR: {type(net_err).__name__}",
                        )

                    # 3. Handle Redirects with re-validation
                    if resp.is_redirect:
                        redirect_count += 1
                        location = resp.headers.get("location")
                        if not location:
                            break
                        current_url = urljoin(current_url, location)
                        continue

                    # 4. Check Content-Type
                    content_type = resp.headers.get("content-type", "").lower()
                    if not any(act in content_type for act in self.ALLOWED_CONTENT_TYPES):
                        return ExtractedPage(
                            url=url,
                            final_url=current_url,
                            title="",
                            content="",
                            content_length=0,
                            http_status=resp.status_code,
                            content_type=content_type,
                            error=f"UNSUPPORTED_CONTENT_TYPE: {content_type}",
                        )

                    # 5. Extract text content if HTTP successful
                    if resp.status_code != 200:
                        return ExtractedPage(
                            url=url,
                            final_url=current_url,
                            title="",
                            content="",
                            content_length=0,
                            http_status=resp.status_code,
                            content_type=content_type,
                            error=f"HTTP_STATUS_{resp.status_code}",
                        )

                    title, text, is_truncated = self._extract_clean_text(resp.text)
                    return ExtractedPage(
                        url=url,
                        final_url=current_url,
                        title=title,
                        content=text,
                        content_length=len(text),
                        http_status=resp.status_code,
                        content_type=content_type,
                        is_truncated=is_truncated,
                    )

                return ExtractedPage(
                    url=url,
                    final_url=current_url,
                    title="",
                    content="",
                    content_length=0,
                    http_status=310,
                    content_type="",
                    error="TOO_MANY_REDIRECTS",
                )

    def _extract_clean_text(self, html_content: str) -> tuple[str, str, bool]:
        """Parse HTML, eliminate scripts/nav/clutter, normalize whitespace, and enforce length bounds."""
        if not html_content or not html_content.strip():
            return "", "", False

        soup = BeautifulSoup(html_content, "html.parser")

        # Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.h1:
            title = soup.h1.get_text(strip=True)

        # Remove irrelevant and noise tags
        unwanted_tags = [
            "script", "style", "noscript", "nav", "footer", "header",
            "aside", "form", "svg", "button", "iframe", "style", "meta",
        ]
        for tag in soup.find_all(unwanted_tags):
            tag.decompose()

        # Extract main text
        raw_text = soup.get_text(separator="\n", strip=True)

        # Normalize whitespace
        cleaned_text = re.sub(r"[ \t]+", " ", raw_text)
        cleaned_text = re.sub(r"\n\s*\n+", "\n\n", cleaned_text).strip()

        # Enforce content length bounds
        is_truncated = False
        if len(cleaned_text) > self.MAX_CONTENT_CHARS:
            cleaned_text = cleaned_text[: self.MAX_CONTENT_CHARS] + "\n...[truncated for length]"
            is_truncated = True

        return title, cleaned_text, is_truncated

    async def fetch_multiple_pages(self, urls: List[str]) -> List[ExtractedPage]:
        """Fetch multiple pages concurrently with bounded concurrency."""
        tasks = [self.fetch_page(u) for u in urls if u and u.strip()]
        if not tasks:
            return []
        return await asyncio.gather(*tasks, return_exceptions=False)


webpage_reader = WebpageReader()
