"""Tests for Kodi-independent service behavior."""

from pathlib import Path

import pytest

from animesubinfo import ExtractedSubtitle
from animesubinfo_kodi import SubtitleService


@pytest.mark.asyncio
async def test_search_returns_ranked_matches_unchanged(sample_subtitle) -> None:
    calls: list[str] = []
    matches = [sample_subtitle]

    async def find(video_name: str):
        calls.append(video_name)
        return matches

    async def download(video_name: str, subtitle_id: int):
        raise AssertionError("download should not be called")

    service = SubtitleService(find, download)

    assert await service.search("Test Anime - 01.mkv") is matches
    assert calls == ["Test Anime - 01.mkv"]


@pytest.mark.asyncio
async def test_search_skips_blank_video_name() -> None:
    async def find(video_name: str):
        raise AssertionError("find should not be called")

    async def download(video_name: str, subtitle_id: int):
        raise AssertionError("download should not be called")

    service = SubtitleService(find, download)

    assert await service.search("  ") == []


@pytest.mark.asyncio
async def test_download_saves_extracted_subtitle(tmp_path: Path) -> None:
    calls: list[tuple[str, int]] = []

    async def find(video_name: str):
        return []

    async def download(video_name: str, subtitle_id: int):
        calls.append((video_name, subtitle_id))
        return ExtractedSubtitle("episode.ass", b"subtitle content")

    service = SubtitleService(find, download)
    destination = tmp_path / "nested" / "profile"

    result = await service.download("Test Anime - 01.mkv", 123, str(destination))

    assert result == str(destination / "episode.ass")
    assert (destination / "episode.ass").read_bytes() == b"subtitle content"
    assert calls == [("Test Anime - 01.mkv", 123)]


@pytest.mark.parametrize(
    ("archive_name", "safe_name"),
    [
        ("../../outside.srt", "outside.srt"),
        (r"..\..\outside.ass", "outside.ass"),
        ("..", "subtitle.srt"),
        ("", "subtitle.srt"),
    ],
)
def test_safe_filename_blocks_archive_paths(
    archive_name: str, safe_name: str
) -> None:
    assert SubtitleService._safe_filename(archive_name) == safe_name
