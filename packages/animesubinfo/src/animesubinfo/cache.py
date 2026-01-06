"""Cache for subtitle search results."""

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Subtitles

CacheKey = tuple[str, str, str]


class SubtitleCache:
    """Thread-safe cache for subtitle search results.

    Manages both cached data and per-key locks for safe concurrent access.
    This allows multiple coroutines to safely share a cache without duplicate
    network requests for the same anime title.

    Example:
        ```
        cache = SubtitleCache()
        # Safe to use concurrently
        results = await asyncio.gather(
            find_best_subtitles("Anime - 01.mkv", cache=cache),
            find_best_subtitles("Anime - 02.mkv", cache=cache),
        )
        ```
    """

    def __init__(self) -> None:
        self._data: dict[CacheKey, list["Subtitles"]] = {}
        self._locks: dict[CacheKey, asyncio.Lock] = {}

    def get_lock(self, key: CacheKey) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        return self._locks[key]

    def get(self, key: CacheKey) -> list["Subtitles"] | None:
        """Get cached subtitles for key, or None if not cached."""
        return self._data.get(key)

    def set(self, key: CacheKey, value: list["Subtitles"]) -> None:
        """Store subtitles for key."""
        self._data[key] = value

    def keys(self) -> list[CacheKey]:
        """Return all cache keys."""
        return list(self._data.keys())

    def __contains__(self, key: CacheKey) -> bool:
        return key in self._data

    def __len__(self) -> int:
        return len(self._data)
