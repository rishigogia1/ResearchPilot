import pytest
from unittest.mock import AsyncMock, patch
import httpx
from app.tools.webpage_reader import (
    ExtractedPage,
    SSRFSecurityError,
    WebpageReader,
    is_prohibited_ip,
    validate_url_safety,
)


def test_is_prohibited_ip():
    # Loopback
    assert is_prohibited_ip("127.0.0.1") is True
    assert is_prohibited_ip("127.0.0.5") is True
    assert is_prohibited_ip("::1") is True

    # Private RFC 1918
    assert is_prohibited_ip("10.0.0.1") is True
    assert is_prohibited_ip("172.16.0.1") is True
    assert is_prohibited_ip("192.168.1.1") is True

    # Cloud metadata IP
    assert is_prohibited_ip("169.254.169.254") is True

    # Public IP
    assert is_prohibited_ip("8.8.8.8") is False
    assert is_prohibited_ip("93.184.216.34") is False


@pytest.mark.asyncio
async def test_validate_url_safety_blocks_prohibited_targets():
    # Localhost
    with pytest.raises(SSRFSecurityError):
        await validate_url_safety("http://localhost:8000/api")

    # Loopback IP
    with pytest.raises(SSRFSecurityError):
        await validate_url_safety("http://127.0.0.1:8000")

    # Cloud metadata IP
    with pytest.raises(SSRFSecurityError):
        await validate_url_safety("http://169.254.169.254/latest/meta-data")

    # Disallowed scheme
    with pytest.raises(SSRFSecurityError):
        await validate_url_safety("file:///etc/passwd")

    with pytest.raises(SSRFSecurityError):
        await validate_url_safety("ftp://ftp.example.com/file")


def test_extract_clean_text():
    reader = WebpageReader()
    raw_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Breakthrough in Sodium-Ion Batteries</title>
        <script>var x = 10; alert('hack');</script>
        <style>body { color: red; }</style>
    </head>
    <body>
        <nav><a href="/">Home</a> <a href="/about">About</a></nav>
        <header><h1>Header Navigation</h1></header>
        <main>
            <p>Researchers have developed a cathode material that increases cycle life to 4,000 cycles.</p>
            <p>The energy density reaches 180 Wh/kg in cylindrical cells.</p>
        </main>
        <footer>Copyright 2026 Example Corp</footer>
    </body>
    </html>
    """
    title, text, is_truncated = reader._extract_clean_text(raw_html)

    assert title == "Breakthrough in Sodium-Ion Batteries"
    assert "Researchers have developed a cathode material" in text
    assert "180 Wh/kg" in text
    # Ensure script, style, nav, and footer were purged
    assert "alert('hack')" not in text
    assert "color: red" not in text
    assert "Header Navigation" not in text
    assert "Copyright 2026" not in text
    assert is_truncated is False


def test_extract_clean_text_truncation():
    reader = WebpageReader()
    # Create HTML larger than MAX_CONTENT_CHARS (6000)
    huge_paragraph = "<p>" + ("Solid electrolyte interfaces improve stability. " * 300) + "</p>"
    raw_html = f"<html><head><title>Long Paper</title></head><body>{huge_paragraph}</body></html>"

    title, text, is_truncated = reader._extract_clean_text(raw_html)
    assert title == "Long Paper"
    assert is_truncated is True
    assert "[truncated for length]" in text
    assert len(text) <= reader.MAX_CONTENT_CHARS + 50


@pytest.mark.asyncio
async def test_fetch_page_ssrf_blocked():
    reader = WebpageReader()
    # Attempting to fetch internal destination returns ExtractedPage with error
    page = await reader.fetch_page("http://127.0.0.1:8080/internal-secrets")
    assert page.http_status == 403
    assert "SSRF_BLOCKED" in (page.error or "")
    assert page.content == ""


@pytest.mark.asyncio
async def test_fetch_page_unsupported_content_type():
    reader = WebpageReader()

    mock_resp = AsyncMock()
    mock_resp.is_redirect = False
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/pdf"}

    with patch("app.tools.webpage_reader.validate_url_safety", new=AsyncMock()):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            page = await reader.fetch_page("https://example.org/report.pdf")
            assert "UNSUPPORTED_CONTENT_TYPE" in (page.error or "")
            assert page.content == ""
