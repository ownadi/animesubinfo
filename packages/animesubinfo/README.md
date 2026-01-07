# animesubinfo

Python client for searching and downloading anime subtitles from [AnimeSub.info](http://animesub.info).

## Installation

```bash
pip install animesubinfo
```

Or with uv:

```bash
uv add animesubinfo
```

## Quick Start

All main functions, types, and exceptions can be imported directly from `animesubinfo`:

```python
from animesubinfo import (
    search,
    find_best_subtitles,
    download_subtitles,
    download_and_extract_subtitle,
    set_default_concurrency,
    ExtractedSubtitle,
    SubtitleCache,
    SortBy,
    TitleType,
    Subtitles,
    SecurityError,
    SessionDataError,
)
```

### Search for subtitles

```python
import asyncio
from animesubinfo import search, SortBy, TitleType

async def main():
    # Simple search
    async for subtitle in search("Naruto"):
        print(f"{subtitle.original_title} - Episode {subtitle.episode}")
        print(f"  Author: {subtitle.author}")
        print(f"  Downloads: {subtitle.downloaded_times}")
        print()

    # Advanced search with filters
    async for subtitle in search(
        "Attack on Titan",
        sort_by=SortBy.DOWNLOADS,
        title_type=TitleType.ENGLISH,
        page_limit=2
    ):
        print(f"{subtitle.english_title} - Episode {subtitle.episode}")

asyncio.run(main())
```

### Find best match for your file

```python
import asyncio
from animesubinfo import find_best_subtitles

async def main():
    # Automatically finds the best subtitle match
    filename = "[HorribleSubs] Attack on Titan - 12 [BD 1080p].mkv"

    subtitle = await find_best_subtitles(filename)

    if subtitle:
        print(f"Best match: {subtitle.original_title}")
        print(f"Episode: {subtitle.episode}")
        print(f"Author: {subtitle.author}")
        print(f"Fitness score: {subtitle.calculate_fitness(filename)}")

asyncio.run(main())
```

### Batch processing with cache

When processing multiple files from the same anime, use `SubtitleCache` to avoid redundant network requests:

```python
import asyncio
from animesubinfo import find_best_subtitles, download_and_extract_subtitle, SubtitleCache

async def main():
    files = [
        "[HorribleSubs] Attack on Titan - 01 [1080p].mkv",
        "[HorribleSubs] Attack on Titan - 02 [1080p].mkv",
        "[HorribleSubs] Attack on Titan - 03 [1080p].mkv",
    ]

    # Shared cache - searches once per title, reuses results for all episodes
    cache = SubtitleCache()

    for filename in files:
        subtitle = await find_best_subtitles(filename, cache=cache)
        if subtitle:
            extracted = await download_and_extract_subtitle(filename, subtitle.id)
            print(f"{filename} -> {extracted.filename}")

asyncio.run(main())
```

The cache is keyed by `(normalized_title, year, season)`, so all episodes of the same anime share cached search results.

### Download subtitles

```python
import asyncio
from animesubinfo import find_best_subtitles, download_subtitles, SecurityError, SessionDataError

async def main():
    filename = "[HorribleSubs] Attack on Titan - 12 [BD 1080p].mkv"

    # Find best match
    subtitle = await find_best_subtitles(filename)

    if subtitle:
        try:
            # Download the subtitle file
            async with download_subtitles(subtitle.id) as download:
                print(f"Downloading: {download.filename}")
                print(f"Size: {download.content_length} bytes")

                # Save to disk
                with open(download.filename, 'wb') as f:
                    async for chunk in download.content:
                        f.write(chunk)

                print("Download complete!")

        except SessionDataError as e:
            print(f"Failed to get session data: {e}")

        except SecurityError as e:
            print(f"Security error: {e}")
            print(f"Debug info - sh: {e.sh}, cookie: {e.cookie}")

asyncio.run(main())
```

### Download and extract subtitle automatically

```python
import asyncio
from animesubinfo import find_best_subtitles, download_and_extract_subtitle

async def main():
    filename = "[HorribleSubs] Attack on Titan - 12 [BD 1080p].mkv"

    # Find best match
    subtitle = await find_best_subtitles(filename)

    if subtitle:
        # Download ZIP and extract the best matching file
        extracted = await download_and_extract_subtitle(filename, subtitle.id)

        print(f"Extracted: {extracted.filename}")
        print(f"Size: {len(extracted.content)} bytes")

        # Save to disk
        with open(extracted.filename, 'wb') as f:
            f.write(extracted.content)

        print("Subtitle saved!")

asyncio.run(main())
```

This function automatically:
- Downloads the subtitle ZIP archive
- Extracts it in memory (no temp files)
- Selects the best matching file based on episode number and metadata
- Falls back to the first file if no matches are found

## API Reference

### `search(phrase, *, sort_by=None, title_type=None, page_limit=None, semaphore=None)`

Search for subtitles on AnimeSub.info.

**Parameters:**
- `phrase` (str): Search query
- `sort_by` (SortBy, optional): Sort order (FITNESS, DOWNLOADS, ADDED_DATE, etc.)
- `title_type` (TitleType, optional): Search in ORIGINAL, ENGLISH, or ALTERNATIVE titles
- `page_limit` (int, optional): Maximum number of pages to fetch
- `semaphore` (asyncio.Semaphore, optional): Semaphore for limiting concurrent requests (default: 3 concurrent)

**Yields:**
- `Subtitles`: Individual subtitle results

### `find_best_subtitles(filename_or_dict, *, normalizer=None, semaphore=None, cache=None)`

Find the best matching subtitles for an anime file.

**Parameters:**
- `filename_or_dict` (str | dict): Anime filename or anitopy-parsed dict
- `normalizer` (callable, optional): Custom normalization function
- `semaphore` (asyncio.Semaphore, optional): Semaphore for limiting concurrent requests (default: 3 concurrent)
- `cache` (SubtitleCache, optional): Cache for storing/retrieving search results by title. Enables efficient batch processing without repeated network requests.

**Returns:**
- `Subtitles | None`: Best matching subtitle or None if not found

### `set_default_concurrency(limit)`

Set the default concurrency limit for network requests.

**Parameters:**
- `limit` (int): Maximum number of concurrent requests (must be >= 1)

### `download_subtitles(subtitle_id, *, semaphore=None)`

Download subtitles as a ZIP file (async context manager).

**Parameters:**
- `subtitle_id` (int): The ID of the subtitle to download
- `semaphore` (asyncio.Semaphore, optional): Semaphore for limiting concurrent requests (default: shared)

**Yields:**
- `DownloadResult`: Named tuple with `filename`, `content` (async iterable), and `content_length`

**Raises:**
- `SessionDataError`: If session data cannot be obtained for the subtitle
- `SecurityError`: If AnimeSub.info returns a security error (HTML instead of ZIP). This typically happens when session tokens are invalid or expired. The exception includes `sh` and `cookie` attributes for debugging.

### `download_and_extract_subtitle(filename_or_dict, subtitle_id, *, normalizer=None, semaphore=None)`

Download subtitle ZIP and automatically extract the best matching file.

**Parameters:**
- `filename_or_dict` (str | dict): Target filename or anitopy-parsed dict to match against
- `subtitle_id` (int): The ID of the subtitle to download
- `normalizer` (callable, optional): Custom normalization function
- `semaphore` (asyncio.Semaphore, optional): Semaphore for limiting concurrent requests (default: shared)

**Returns:**
- `ExtractedSubtitle`: Named tuple with `filename` (str) and `content` (bytes)

**Raises:**
- `SessionDataError`: If session data cannot be obtained
- `SecurityError`: If AnimeSub.info returns a security error
- `ValueError`: Only if the archive is completely empty

**Behavior:**
- For single-file archives: Returns that file
- For multi-file archives: Calculates fitness score based on:
  - Episode number (must match)
  - Subtitle extension preference (.srt, .ass, .ssa, .sub, .vtt)
  - File metadata (checksum, source, release group, resolution, video terms)
- If no files match (all scores are 0): Returns the first file in the archive
- Extracts in memory without creating temporary files

## Exception Handling

### `SessionDataError`

Raised when session data (sh token and cookie) cannot be obtained for a subtitle.

**Attributes:**
- `subtitle_id` (int): The ID of the subtitle that failed

### `SecurityError`

Raised when AnimeSub.info returns a security error ("błąd zabezpieczeń"). This happens when the server returns HTML instead of a ZIP file, typically due to invalid or expired session tokens.

**Attributes:**
- `subtitle_id` (int): The ID of the subtitle that failed
- `sh` (str): The sh token that was used (for debugging)
- `cookie` (str): The cookie value that was used (for debugging)

## Development

### Setup

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (from workspace root)
cd ../..
uv sync --all-packages

# Run tests for this package
uv run --package animesubinfo pytest
```

### Running tests

```bash
uv run --package animesubinfo pytest
```
