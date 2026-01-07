"""Tests for download_and_extract_subtitle function."""

import io
import asyncio
import zipfile
from contextlib import asynccontextmanager
from typing import Any, Optional, cast
from unittest.mock import patch

import anitopy
import pytest

from animesubinfo.api import (
    DownloadResult,
    ExtractedSubtitle,
    download_and_extract_subtitle,
)


def create_test_zip(*files: tuple[str, bytes]) -> bytes:
    """Create a test ZIP file in memory.

    Args:
        *files: Tuples of (filename, content) to add to the ZIP

    Returns:
        ZIP file content as bytes
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files:
            zip_file.writestr(filename, content)
    return zip_buffer.getvalue()


def mock_download_subtitles(zip_content: bytes):
    """Create a mock for download_subtitles that returns ZIP content."""

    @asynccontextmanager
    async def _mock_download(subtitle_id: int, *, semaphore: Optional[asyncio.Semaphore]=None):
        """Mock download_subtitles context manager."""

        async def async_iter():
            """Yield ZIP content in chunks."""
            yield zip_content

        download_result = DownloadResult(
            filename="test.zip", content=async_iter(), content_length=len(zip_content)
        )
        yield download_result

    return _mock_download


@pytest.mark.asyncio
async def test_single_file_archive():
    """Test extraction from archive with single subtitle file."""
    zip_content = create_test_zip(
        ("Fumetsu no Anata e S3 - 03.ass", b"subtitle content here")
    )

    with patch(
        "animesubinfo.api.download_subtitles", mock_download_subtitles(zip_content)
    ):
        result = await download_and_extract_subtitle(
            "Fumetsu no Anata e S3 - 03 [1080p].mkv", subtitle_id=12345
        )

        assert isinstance(result, ExtractedSubtitle)
        assert result.filename == "Fumetsu no Anata e S3 - 03.ass"
        assert result.content == b"subtitle content here"


@pytest.mark.asyncio
async def test_multiple_files_episode_match():
    """Test extraction from archive with multiple episodes."""
    zip_content = create_test_zip(
        ("End of Evangelion - 25.srt", b"episode 25 content"),
        ("End of Evangelion - 26.srt", b"episode 26 content"),
    )

    with patch(
        "animesubinfo.api.download_subtitles", mock_download_subtitles(zip_content)
    ):
        result = await download_and_extract_subtitle(
            "End of Evangelion - 26.mkv", subtitle_id=12345
        )

        assert result.filename == "End of Evangelion - 26.srt"
        assert result.content == b"episode 26 content"


@pytest.mark.asyncio
async def test_pack_with_many_episodes():
    """Test extraction from a pack with many episodes."""
    files: list[tuple[str, bytes]] = []
    for ep in range(1, 11):
        files.append(
            (
                f"GTO - {ep:02d} [DVDRip 768x576 x264 AC3].ass",
                f"episode {ep}".encode(),
            )
        )

    zip_content = create_test_zip(*files)

    with patch(
        "animesubinfo.api.download_subtitles", mock_download_subtitles(zip_content)
    ):
        result = await download_and_extract_subtitle(
            "[SubGroup] GTO - 05 [1080p].mkv", subtitle_id=12345
        )

        assert result.filename == "GTO - 05 [DVDRip 768x576 x264 AC3].ass"
        assert result.content == b"episode 5"


@pytest.mark.asyncio
async def test_mixed_files_prefers_best_match():
    """Test that best matching file is selected via fitness scoring."""
    zip_content = create_test_zip(
        ("Attack on Titan - 12.ass", b"subtitle content"),
        ("Attack on Titan - 11.ass", b"wrong episode"),
        ("README.txt", b"readme content"),
    )

    with patch(
        "animesubinfo.api.download_subtitles", mock_download_subtitles(zip_content)
    ):
        result = await download_and_extract_subtitle(
            "Attack on Titan - 12.mkv", subtitle_id=12345
        )

        assert result.filename == "Attack on Titan - 12.ass"
        assert result.content == b"subtitle content"


@pytest.mark.asyncio
async def test_different_release_groups():
    """Test matching when archive contains multiple release groups."""
    zip_content = create_test_zip(
        ("[GroupA] Anime Title - 01 [1080p].ass", b"GroupA subtitle"),
        ("[GroupB] Anime Title - 01 [720p].ass", b"GroupB subtitle"),
    )

    with patch(
        "animesubinfo.api.download_subtitles", mock_download_subtitles(zip_content)
    ):
        result = await download_and_extract_subtitle(
            "[GroupA] Anime Title - 01 [1080p].mkv", subtitle_id=12345
        )

        # Should match GroupA (better fitness due to release group + resolution match)
        assert result.filename == "[GroupA] Anime Title - 01 [1080p].ass"
        assert result.content == b"GroupA subtitle"


@pytest.mark.asyncio
async def test_movie_without_episode_number():
    """Test matching movie files (no episode number)."""
    zip_content = create_test_zip(
        ("Your Name [1080p].srt", b"movie subtitle"),
    )

    with patch(
        "animesubinfo.api.download_subtitles", mock_download_subtitles(zip_content)
    ):
        result = await download_and_extract_subtitle(
            "[SubGroup] Your Name [1080p BluRay].mkv", subtitle_id=12345
        )

        assert result.filename == "Your Name [1080p].srt"
        assert result.content == b"movie subtitle"


@pytest.mark.asyncio
async def test_empty_archive_error():
    """Test error when archive is empty."""
    zip_content = create_test_zip()

    with patch(
        "animesubinfo.api.download_subtitles", mock_download_subtitles(zip_content)
    ):
        with pytest.raises(ValueError, match="Empty archive"):
            await download_and_extract_subtitle("Anime - 01.mkv", subtitle_id=12345)


@pytest.mark.asyncio
async def test_no_matching_episode_returns_first():
    """Test that when no file matches, the first file is returned."""
    files = [(f"Anime - {i}.srt", f"episode {i}".encode()) for i in range(1, 6)]
    zip_content = create_test_zip(*files)

    with patch(
        "animesubinfo.api.download_subtitles", mock_download_subtitles(zip_content)
    ):
        # Request episode 10 (not in archive) - should return first file
        result = await download_and_extract_subtitle(
            "Anime - 10.mkv", subtitle_id=12345
        )

        # Should return the first file as fallback
        assert result.filename == "Anime - 1.srt"
        assert result.content == b"episode 1"


@pytest.mark.asyncio
async def test_with_anitopy_dict():
    """Test using anitopy dict instead of filename string."""
    zip_content = create_test_zip(
        ("Attack on Titan - 12.srt", b"subtitle content"),
    )

    with patch(
        "animesubinfo.api.download_subtitles", mock_download_subtitles(zip_content)
    ):
        # Parse filename with anitopy
        parsed = cast(
            dict[str, Any],
            anitopy.parse("[HorribleSubs] Attack on Titan - 12 [1080p].mkv"),  # type: ignore[misc]
        )

        result = await download_and_extract_subtitle(parsed, subtitle_id=12345)

        assert result.filename == "Attack on Titan - 12.srt"
        assert result.content == b"subtitle content"


@pytest.mark.asyncio
async def test_resolution_matching():
    """Test that resolution is considered in fitness scoring."""
    zip_content = create_test_zip(
        ("Anime - 01 [720p].ass", b"720p subtitle"),
        ("Anime - 01 [1080p].ass", b"1080p subtitle"),
    )

    with patch(
        "animesubinfo.api.download_subtitles", mock_download_subtitles(zip_content)
    ):
        # Request 1080p
        result = await download_and_extract_subtitle(
            "Anime - 01 [1080p].mkv", subtitle_id=12345
        )

        # Should prefer 1080p version
        assert result.filename == "Anime - 01 [1080p].ass"
        assert result.content == b"1080p subtitle"
