"""Tests for download_subtitles function."""

import httpx
import pytest
import respx
from unittest.mock import ANY, AsyncMock, patch

from animesubinfo.api import download_subtitles, SessionData
from animesubinfo.exceptions import SecurityError, SessionDataError


@pytest.mark.asyncio
@respx.mock
async def test_download_subtitles_basic():
    """Test basic download with filename and content."""
    # Mock search_by_id to return session data
    with patch("animesubinfo.api._search_by_id", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = SessionData(
            sh="test_sh_value", ansi_cookie="test_cookie"
        )

        # Mock the POST request
        respx.post(
            "http://animesub.info/sciagnij.php",
            data={"id": "12345", "sh": "test_sh_value"},
            headers__contains={"cookie": "ansi_sciagnij=test_cookie"},
        ).mock(
            return_value=httpx.Response(
                200,
                content=b"fake zip content",
                headers={
                    "content-disposition": 'attachment; filename="test_subtitle.zip"',
                    "content-length": "16",
                },
            )
        )

        # Download the subtitle by ID
        async with download_subtitles(12345) as download:
            assert download.filename == "test_subtitle.zip"
            assert download.content_length == 16

            # Collect all content chunks
            content = b""
            async for chunk in download.content:
                content += chunk

            assert content == b"fake zip content"

        # Verify _search_by_id was called
        mock_search.assert_called_once_with(12345, ANY)


@pytest.mark.asyncio
@respx.mock
async def test_download_subtitles_filename_with_quotes():
    """Test parsing filename with quotes in Content-Disposition."""
    with patch("animesubinfo.api._search_by_id", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = SessionData(sh="sh_value", ansi_cookie="cookie")

        respx.post("http://animesub.info/sciagnij.php").mock(
            return_value=httpx.Response(
                200,
                content=b"",
                headers={"content-disposition": 'attachment; filename="my file.zip"'},
            )
        )

        async with download_subtitles(222) as download:
            assert download.filename == "my file.zip"


@pytest.mark.asyncio
@respx.mock
async def test_download_subtitles_http_error():
    """Test handling of HTTP errors."""
    with patch("animesubinfo.api._search_by_id", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = SessionData(sh="sh_value", ansi_cookie="cookie")

        respx.post("http://animesub.info/sciagnij.php").mock(
            return_value=httpx.Response(404, text="Not Found")
        )

        with pytest.raises(httpx.HTTPStatusError):
            async with download_subtitles(555) as download:
                _ = download.filename


@pytest.mark.asyncio
@respx.mock
async def test_download_subtitles_early_exit():
    """Test that resources are cleaned up when exiting context early."""
    with patch("animesubinfo.api._search_by_id", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = SessionData(sh="sh_value", ansi_cookie="cookie")

        respx.post("http://animesub.info/sciagnij.php").mock(
            return_value=httpx.Response(
                200,
                content=b"large content that we won't fully consume",
                headers={"content-disposition": 'filename="test.zip"'},
            )
        )

        # Exit context without consuming all content - just verify it doesn't raise
        async with download_subtitles(666) as download:
            # Verify download object exists but don't consume content
            _ = download.filename

        # Test passes if no resource warnings or errors occur


@pytest.mark.asyncio
async def test_download_subtitles_session_data_error():
    """Test SessionDataError when session data cannot be obtained."""
    with patch("animesubinfo.api._search_by_id", new_callable=AsyncMock) as mock_search:
        # Mock search_by_id to return None (no session data)
        mock_search.return_value = None

        with pytest.raises(SessionDataError) as exc_info:
            async with download_subtitles(999) as download:
                _ = download.filename

        # Verify exception details
        assert exc_info.value.subtitle_id == 999
        assert "Could not obtain session data" in str(exc_info.value)


@pytest.mark.asyncio
@respx.mock
async def test_download_subtitles_security_error():
    """Test SecurityError when AnimeSub.info returns HTML instead of ZIP."""
    with patch("animesubinfo.api._search_by_id", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = SessionData(
            sh="test_sh_value_12345678901234567890",
            ansi_cookie="test_cookie_12345678901234567890",
        )

        # Mock POST request to return HTML (security error)
        respx.post("http://animesub.info/sciagnij.php").mock(
            return_value=httpx.Response(
                200,
                content=b"<html><body>Blad zabezpieczen</body></html>",
                headers={"content-type": "text/html; charset=iso-8859-2"},
            )
        )

        with pytest.raises(SecurityError) as exc_info:
            async with download_subtitles(888) as download:
                _ = download.filename

        # Verify exception details
        assert exc_info.value.subtitle_id == 888
        assert exc_info.value.sh == "test_sh_value_12345678901234567890"
        assert exc_info.value.cookie == "test_cookie_12345678901234567890"
        assert "Security error" in str(exc_info.value)
        assert "session tokens may be invalid" in str(exc_info.value)
