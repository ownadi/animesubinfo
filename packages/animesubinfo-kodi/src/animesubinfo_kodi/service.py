"""Kodi-independent subtitle service logic."""

from collections.abc import Awaitable, Callable
from pathlib import Path

from animesubinfo import ExtractedSubtitle, SubtitleMatch

FindSubtitleMatches = Callable[[str], Awaitable[list[SubtitleMatch]]]
DownloadSubtitle = Callable[[str, int], Awaitable[ExtractedSubtitle]]


class SubtitleService:
    """Find and download subtitles using the core package."""

    def __init__(self, find: FindSubtitleMatches, download: DownloadSubtitle) -> None:
        self._find = find
        self._download = download

    async def search(self, video_name: str) -> list[SubtitleMatch]:
        """Return ranked subtitle matches for a non-empty video name."""
        if not video_name.strip():
            return []
        return await self._find(video_name)

    async def download(
        self, video_name: str, subtitle_id: int, destination: str
    ) -> str:
        """Download a subtitle and save it inside Kodi's profile directory."""
        subtitle = await self._download(video_name, subtitle_id)
        filename = self._safe_filename(subtitle.filename)
        destination_path = Path(destination)
        destination_path.mkdir(parents=True, exist_ok=True)
        path = destination_path / filename
        path.write_bytes(subtitle.content)
        return str(path)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        """Prevent archive filenames from escaping Kodi's profile directory."""
        safe = Path(filename.replace("\\", "/")).name
        if safe in {"", ".", ".."}:
            return "subtitle.srt"
        return safe
