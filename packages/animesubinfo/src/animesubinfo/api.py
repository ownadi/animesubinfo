import asyncio
import io
import re
import zipfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterable,
    Callable,
    List,
    NamedTuple,
    Optional,
    cast,
)

import anitopy  # type: ignore[import-untyped]
import httpx

from .cache import CacheKey, SubtitleCache
from .exceptions import SecurityError, SessionDataError
from .models import SortBy, Subtitles, TitleType
from .parsers.catalog_parser import CatalogParser
from .parsers.search_results_parser import SearchResultsParser
from .utils import normalize as default_normalize

# Default semaphore for limiting concurrent requests (shared across all functions)
_default_semaphore: Optional[asyncio.Semaphore] = None
_default_concurrency: int = 3


def set_default_concurrency(limit: int) -> None:
    """Set the default concurrency limit for network requests.

    This affects all functions that make concurrent requests (search,
    find_best_subtitles) when no explicit semaphore is provided.

    Args:
        limit: Maximum number of concurrent requests (must be >= 1)

    Example:
        ```
        from animesubinfo import set_default_concurrency

        # Allow up to 5 concurrent requests
        set_default_concurrency(5)
        ```
    """
    global _default_concurrency, _default_semaphore
    if limit < 1:
        raise ValueError("Concurrency limit must be at least 1")
    _default_concurrency = limit
    _default_semaphore = None  # Reset so next call creates new semaphore


def _get_default_semaphore() -> asyncio.Semaphore:
    """Get or create the shared default semaphore."""
    global _default_semaphore
    if _default_semaphore is None:
        _default_semaphore = asyncio.Semaphore(_default_concurrency)

    return _default_semaphore


class DownloadResult(NamedTuple):
    """Download result containing subtitle file metadata and streaming content.

    Attributes:
        filename: Name of the downloaded subtitle archive file
        content: Async iterator yielding file content in chunks
        content_length: Total size in bytes, or None if unavailable
    """

    filename: str
    content: AsyncIterable[bytes]
    content_length: Optional[int]


class SessionData(NamedTuple):
    """Session data required for downloading subtitles.

    Attributes:
        sh: Security token from the search result form
        ansi_cookie: Session cookie value
    """

    sh: str
    ansi_cookie: str


async def search(
    phrase: str,
    *,
    sort_by: Optional[SortBy] = None,
    title_type: Optional[TitleType] = None,
    page_limit: Optional[int] = None,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> AsyncGenerator[Subtitles, None]:
    """Search for subtitles on AnimeSub.info.

    Args:
        phrase: Search phrase
        sort_by: Sort order for results
        title_type: Type of title to search in
        page_limit: Maximum number of pages to fetch
        semaphore: Semaphore for limiting concurrent requests (default: 3 concurrent)

    Yields:
        Subtitles results in order by page
    """
    base_url = "http://animesub.info/szukaj.php"

    async with httpx.AsyncClient(default_encoding="iso-8859-2") as client:
        # Fetch and parse first page
        params = {
            "szukane": phrase,
        }

        if sort_by:
            params["pSortuj"] = sort_by.value
        if title_type:
            params["pTitle"] = title_type.value

        async with client.stream("GET", base_url, params=params) as response:
            response.raise_for_status()

            # Extract ansi_sciagnij cookie
            ansi_cookie = response.cookies.get("ansi_sciagnij", "")

            # Parse first page by streaming chunks
            parser = SearchResultsParser(ansi_cookie=ansi_cookie)
            async for chunk in response.aiter_text():
                parser.feed(chunk)

        first_page_results = parser.subtitles_list
        total_pages = parser.number_of_pages

        # Apply page limit if specified
        if page_limit:
            total_pages = min(total_pages, page_limit)

        # Single page case - yield results and return early
        if total_pages == 1:
            for subtitle in first_page_results:
                yield subtitle
            return

        # Use provided semaphore or shared default
        if semaphore is None:
            semaphore = _get_default_semaphore()

        async def fetch_and_parse_page(
            page_num: int,
        ) -> tuple[int, List[Subtitles]]:
            """Fetch and parse a single page with concurrency limit."""
            async with semaphore:
                page_params = params.copy()
                page_params["od"] = str(page_num - 1)  # 0-based pagination

                page_parser = SearchResultsParser(ansi_cookie=ansi_cookie)
                async with client.stream(
                    "GET", base_url, params=page_params
                ) as page_response:
                    page_response.raise_for_status()
                    async for chunk in page_response.aiter_text():
                        page_parser.feed(chunk)

                return page_num, page_parser.subtitles_list

        async with asyncio.TaskGroup() as tg:
            # Schedule all remaining pages
            tasks = [
                tg.create_task(fetch_and_parse_page(page_num))
                for page_num in range(2, total_pages + 1)
            ]

            # Now yield first page results after scheduling
            for subtitle in first_page_results:
                yield subtitle

            # Collect results in a dict to maintain order
            results_map: dict[int, List[Subtitles]] = {}
            next_page_to_yield = 2

            # Process results as they complete
            for coro in asyncio.as_completed(tasks):
                page_num, page_results = await coro
                results_map[page_num] = page_results

                # Yield any consecutive pages that are ready
                while next_page_to_yield in results_map:
                    for subtitle in results_map[next_page_to_yield]:
                        yield subtitle
                    del results_map[next_page_to_yield]
                    next_page_to_yield += 1


async def _search_by_id(
    subtitle_id: int,
    semaphore: asyncio.Semaphore,
) -> Optional[SessionData]:
    """Search for a subtitle by ID and extract fresh session data.

    Args:
        subtitle_id: The ID of the subtitle to search for
        semaphore: Semaphore for limiting concurrent requests

    Returns:
        SessionData with sh and ansi_cookie if found, None otherwise
    """
    base_url = "http://animesub.info/szukaj.php"

    async with semaphore:
        async with httpx.AsyncClient(default_encoding="iso-8859-2") as client:
            params = {"ID": str(subtitle_id)}

            async with client.stream("GET", base_url, params=params) as response:
                response.raise_for_status()

                # Extract ansi_sciagnij cookie
                ansi_cookie = response.cookies.get("ansi_sciagnij", "")

                # Parse response to extract sh value
                parser = SearchResultsParser(ansi_cookie=ansi_cookie)
                async for chunk in response.aiter_text():
                    parser.feed(chunk)

            # Get the sh value for this subtitle id
            sh = parser.get_sh_for_id(subtitle_id)
            if not sh or not ansi_cookie:
                return None

            return SessionData(sh=sh, ansi_cookie=ansi_cookie)


@asynccontextmanager
async def download_subtitles(
    subtitle_id: int,
    *,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> AsyncIterator[DownloadResult]:
    """Download subtitles as a ZIP file from AnimeSub.info.

    Args:
        subtitle_id: The ID of the subtitle to download
        semaphore: Semaphore for limiting concurrent requests (default: shared)

    Yields:
        DownloadResult with filename, content iterator, and content_length

    Raises:
        SessionDataError: If session data cannot be obtained for the subtitle
        SecurityError: If AnimeSub.info returns a security error (HTML instead of ZIP)

    Example:
        ```
        async with download_subtitles(12345) as download:
            print(f"Downloading {download.filename} ({download.content_length} bytes)")
            with open(download.filename, 'wb') as f:
                async for chunk in download.content:
                    f.write(chunk)
        ```
    """
    if semaphore is None:
        semaphore = _get_default_semaphore()

    # Get fresh session data by searching for this subtitle
    session = await _search_by_id(subtitle_id, semaphore)
    if not session:
        raise SessionDataError(subtitle_id)

    url = "http://animesub.info/sciagnij.php"

    async with semaphore:
        client = httpx.AsyncClient(
            cookies={"ansi_sciagnij": session.ansi_cookie},
            default_encoding="iso-8859-2",
        )
        response = None
        try:
            response = await client.post(
                url,
                data={"id": str(subtitle_id), "sh": session.sh},
            )
            response.raise_for_status()

            # Check for security error (HTML response instead of ZIP)
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                raise SecurityError(subtitle_id, session.sh, session.ansi_cookie)

            # Extract filename from Content-Disposition header
            filename = "subtitle.zip"  # default fallback
            content_disposition = response.headers.get("content-disposition", "")
            if content_disposition:
                # Parse filename from header like: attachment; filename="file.zip"
                match = re.search(r'filename="?([^"]+)"?', content_disposition)
                if match:
                    filename = match.group(1)

            # Extract content length
            content_length = None
            if "content-length" in response.headers:
                content_length = int(response.headers["content-length"])

            yield DownloadResult(
                filename=filename,
                content=response.aiter_bytes(),
                content_length=content_length,
            )
        finally:
            if response is not None:
                await response.aclose()
            await client.aclose()


def _calculate_file_fitness(
    target_parsed: dict[str, Any], zip_filename: str, normalizer: Callable[[str], str]
) -> int:
    """Calculate fitness score for a file in the ZIP archive.

    Note: Title matching is NOT performed here since the ZIP was already selected
    for the correct title. This function focuses on episode number and metadata matching.

    Args:
        target_parsed: anitopy-parsed dict of the target filename
        zip_filename: Name of file in the ZIP archive
        normalizer: Normalization function for text comparison

    Returns:
        Fitness score (higher is better, 0 means no match)
    """
    # Parse the ZIP filename
    zip_parsed = cast(dict[str, Any], anitopy.parse(zip_filename) or {})  # type: ignore[misc]

    # Match episode number (hard requirement)
    target_episode = str(target_parsed.get("episode_number", ""))
    zip_episode = str(zip_parsed.get("episode_number", ""))

    # Handle movies (no episode number)
    if not target_episode and not zip_episode:
        # Both are movies, proceed with base score
        result = 1
    elif not target_episode or not zip_episode:
        # One is movie, one is not - no match
        return 0
    elif target_episode != zip_episode:
        # Different episode numbers - no match
        return 0
    else:
        # Episode numbers match
        result = 1

    # Add bonus for recognized subtitle extensions
    subtitle_extensions = [".srt", ".ass", ".ssa", ".sub", ".vtt"]
    if any(zip_filename.lower().endswith(ext) for ext in subtitle_extensions):
        result += 10  # Prefer subtitle files over other text files

    # Helper to get parsed values
    def get_values(parsed: dict[str, Any], key: str) -> list[str]:
        value = parsed.get(key, "")
        if not value:
            return []
        if isinstance(value, list):
            return [str(v) for v in value]  # type: ignore[misc]
        return [str(value)]

    # Tier 1: File checksum, Source (most important metadata)
    tier1_count = 0

    target_checksums = get_values(target_parsed, "file_checksum")
    zip_checksums = get_values(zip_parsed, "file_checksum")
    if target_checksums and zip_checksums:
        if any(
            normalizer(tc) == normalizer(zc)
            for tc in target_checksums
            for zc in zip_checksums
        ):
            tier1_count += 1

    target_sources = get_values(target_parsed, "source")
    zip_sources = get_values(zip_parsed, "source")
    if target_sources and zip_sources:
        if any(
            normalizer(ts) == normalizer(zs)
            for ts in target_sources
            for zs in zip_sources
        ):
            tier1_count += 1

    result = (result << 3) | tier1_count

    # Tier 2: Release group
    tier2_count = 0
    target_groups = get_values(target_parsed, "release_group")
    zip_groups = get_values(zip_parsed, "release_group")
    if target_groups and zip_groups:
        if any(
            normalizer(tg) == normalizer(zg)
            for tg in target_groups
            for zg in zip_groups
        ):
            tier2_count = 1

    result = (result << 1) | tier2_count

    # Tier 3: Resolution, Video term
    tier3_count = 0

    target_res = get_values(target_parsed, "video_resolution")
    zip_res = get_values(zip_parsed, "video_resolution")
    if target_res and zip_res:
        if any(normalizer(tr) == normalizer(zr) for tr in target_res for zr in zip_res):
            tier3_count += 1

    target_vt = get_values(target_parsed, "video_term")
    zip_vt = get_values(zip_parsed, "video_term")
    if target_vt and zip_vt:
        if any(normalizer(tv) == normalizer(zv) for tv in target_vt for zv in zip_vt):
            tier3_count += 1

    result = (result << 4) | tier3_count

    return result


class ExtractedSubtitle(NamedTuple):
    """Extracted subtitle file from a ZIP archive.

    Attributes:
        filename: Name of the subtitle file
        content: File content as bytes
    """

    filename: str
    content: bytes


async def download_and_extract_subtitle(
    filename_or_dict: str | dict[str, Any],
    subtitle_id: int,
    *,
    normalizer: Optional[Callable[[str], str]] = None,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> ExtractedSubtitle:
    """Download subtitle ZIP and extract the best matching file.

    This function:
    1. Downloads the subtitle ZIP using download_subtitles()
    2. Extracts it in memory (no temp files)
    3. Scores all files using fitness calculation
    4. Returns the file with the highest fitness score (or first file if no matches)

    Args:
        filename_or_dict: Target filename string or anitopy-parsed dict to match
        subtitle_id: ID of the subtitle to download
        normalizer: Optional custom normalization function
        semaphore: Semaphore for limiting concurrent requests (default: shared)

    Returns:
        ExtractedSubtitle with filename and content of the best matching file.
        If no files match (all scores are 0), returns the first file in the archive.

    Raises:
        SessionDataError: If session data cannot be obtained
        SecurityError: If AnimeSub.info returns a security error
        ValueError: Only raised if the archive is completely empty

    Example:
        ```
        # Match against a filename
        subtitle = await download_and_extract_subtitle(
            "[HorribleSubs] Attack on Titan - 12 [1080p].mkv",
            subtitle_id=12345
        )

        # Or use anitopy dict
        parsed = anitopy.parse(filename)
        subtitle = await download_and_extract_subtitle(parsed, subtitle_id=12345)

        # Save the file
        with open(subtitle.filename, 'wb') as f:
            f.write(subtitle.content)
        ```
    """
    norm = normalizer or default_normalize

    # Parse target filename
    target_parsed: dict[str, Any]
    if isinstance(filename_or_dict, str):
        target_parsed = cast(dict[str, Any], anitopy.parse(filename_or_dict) or {})  # type: ignore[misc]
    else:
        target_parsed = filename_or_dict

    # Download the ZIP
    async with download_subtitles(subtitle_id, semaphore=semaphore) as download:
        # Collect ZIP content in memory
        zip_content = io.BytesIO()
        async for chunk in download.content:
            zip_content.write(chunk)

        zip_content.seek(0)

    # Extract and analyze files
    with zipfile.ZipFile(zip_content, "r") as zip_file:
        # Get all files in the archive
        all_files = zip_file.namelist()

        if not all_files:
            raise ValueError(f"Empty archive (ID: {subtitle_id})")

        # Single file case - easy
        if len(all_files) == 1:
            filename = all_files[0]
            content = zip_file.read(filename)
            # Use just the filename without path
            return ExtractedSubtitle(filename=Path(filename).name, content=content)

        # Multiple files - calculate fitness scores for all files
        best_file: Optional[str] = None
        best_score = 0

        for filename in all_files:
            score = _calculate_file_fitness(target_parsed, filename, norm)
            if score > best_score:
                best_score = score
                best_file = filename

        # If no matches found (all scores are 0), fall back to first file
        if not best_file or best_score == 0:
            best_file = all_files[0]

        content = zip_file.read(best_file)
        return ExtractedSubtitle(filename=Path(best_file).name, content=content)


async def _iter_title_subtitles(
    parsed: dict[str, Any],
    normalizer: Callable[[str], str],
    semaphore: Optional[asyncio.Semaphore],
    cache: Optional[SubtitleCache],
    cache_key: CacheKey,
) -> AsyncGenerator[Subtitles, None]:
    """Yield subtitles from cache or network.

    This async generator provides a unified interface for iterating over subtitles,
    regardless of whether they come from cache or network. On cache miss, it fetches
    from the network, yields results as they stream in, and populates the cache.

    When a cache is provided, uses per-key locking to ensure only one coroutine
    fetches data for a given title, even under concurrent access.

    Yields:
        Subtitles objects as they become available
    """
    # No cache - just fetch from network
    if cache is None:
        async for subtitle in _fetch_title_subtitles(parsed, normalizer, semaphore):
            yield subtitle
        return

    # Acquire lock to prevent duplicate fetches
    lock = cache.get_lock(cache_key)
    async with lock:
        cached = cache.get(cache_key)
        if cached is not None:
            # Cache hit - will yield outside lock
            pass
        else:
            # Cache miss - fetch and populate
            accumulated: list[Subtitles] = []
            async for subtitle in _fetch_title_subtitles(parsed, normalizer, semaphore):
                accumulated.append(subtitle)
                yield subtitle

            cache.set(cache_key, accumulated)
            return

    # Yield cached data outside the lock
    for subtitle in cached:
        yield subtitle


async def _fetch_title_subtitles(
    parsed: dict[str, Any],
    normalizer: Callable[[str], str],
    semaphore: Optional[asyncio.Semaphore],
) -> AsyncGenerator[Subtitles, None]:
    """Fetch subtitles from AnimeSub.info network.

    Internal helper that handles catalog lookup and paginated search.

    Yields:
        Subtitles objects as they are fetched from pages
    """
    title = str(parsed.get("anime_title", ""))
    if not title:
        return

    # Extract season and year for catalog matching
    anime_season = parsed.get("anime_season")
    anime_year = parsed.get("anime_year")

    # Get first letter for catalog URL
    first_letter = title[0].lower()
    catalog_url = f"http://animesub.info/katalog.php?S={first_letter}"

    async with httpx.AsyncClient(default_encoding="iso-8859-2") as client:
        # Step 1: Parse catalog to find search path
        catalog_parser = CatalogParser(
            title,
            season=str(anime_season) if anime_season else None,
            year=str(anime_year) if anime_year else None,
            normalizer=normalizer,
        )
        search_path = None
        async with client.stream("GET", catalog_url) as response:
            response.raise_for_status()
            async for chunk in response.aiter_text():
                search_path = catalog_parser.feed_and_get_result(chunk)
                if search_path:
                    break  # Found match, stop downloading

        if not search_path:
            return

        # Step 2: Parse first page to get total pages
        search_url = f"http://animesub.info/{search_path}"

        ansi_cookie = ""
        first_parser: Optional[SearchResultsParser] = None

        async with client.stream("GET", search_url) as search_response:
            search_response.raise_for_status()

            # Extract ansi_sciagnij cookie from first response
            ansi_cookie = search_response.cookies.get("ansi_sciagnij", "")

            # Create parser with the cookie and parse streaming chunks
            first_parser = SearchResultsParser(ansi_cookie=ansi_cookie)
            async for chunk in search_response.aiter_text():
                first_parser.feed(chunk)

        if not first_parser:
            return

        first_page_results = first_parser.subtitles_list
        total_pages = first_parser.number_of_pages

        if not first_page_results:
            return

        # Yield first page results
        for subtitle in first_page_results:
            yield subtitle

        # Single page case - done
        if total_pages == 1:
            return

        # Multiple pages - fetch concurrently
        # Use provided semaphore or shared default
        if semaphore is None:
            semaphore = _get_default_semaphore()

        async def fetch_and_parse_page(page_num: int) -> List[Subtitles]:
            """Fetch and parse a single page with concurrency limit."""
            async with semaphore:
                # Parse URL to extract params
                from urllib.parse import parse_qs, urlparse

                parsed_url = urlparse(search_path)
                params = parse_qs(parsed_url.query)

                # Convert to dict with single values
                page_params = {k: v[0] for k, v in params.items()}
                page_params["od"] = str(page_num - 1)  # 0-based pagination

                page_url = f"http://animesub.info/{parsed_url.path}"
                page_parser = SearchResultsParser(ansi_cookie=ansi_cookie)
                async with client.stream(
                    "GET", page_url, params=page_params
                ) as page_response:
                    page_response.raise_for_status()
                    async for chunk in page_response.aiter_text():
                        page_parser.feed(chunk)

                return page_parser.subtitles_list

        async with asyncio.TaskGroup() as tg:
            # Schedule all remaining pages immediately
            tasks = [
                tg.create_task(fetch_and_parse_page(page_num))
                for page_num in range(2, total_pages + 1)
            ]

            # Yield results from remaining pages as they arrive
            for coro in asyncio.as_completed(tasks):
                page_results = await coro
                for subtitle in page_results:
                    yield subtitle


async def find_best_subtitles(
    filename_or_dict: str | dict[str, Any],
    *,
    normalizer: Optional[Callable[[str], str]] = None,
    semaphore: Optional[asyncio.Semaphore] = None,
    cache: Optional[SubtitleCache] = None,
) -> Optional[Subtitles]:
    """Find the best matching subtitles for a given anime file.

    This function:
    1. Extracts anime title from filename/dict using anitopy
    2. Parses the AnimeSub.info catalog to find the title
    3. Searches all subtitles for that title (across all pages concurrently)
    4. Calculates fitness scores for each subtitle against the provided file
    5. Returns the subtitle with the highest score

    Args:
        filename_or_dict: Filename string or anitopy-parsed dict to match against
        normalizer: Optional custom normalization function (defaults to project's normalize)
        semaphore: Semaphore for limiting concurrent requests (default: 3 concurrent)
        cache: Optional cache dict for storing/retrieving search results by title.
            When provided, results are cached by (normalized_title, year, season).
            This enables efficient batch processing of multiple files from the same
            anime title without repeated network requests.

    Returns:
        Subtitles object with highest fitness score, or None if no match found

    Example:
        ```
        # Single file
        best = await find_best_subtitles(
            "[HorribleSubs] Attack on Titan - 12 [BD 1080p].mkv"
        )

        # Batch processing with cache
        cache: SubtitleCache = {}
        for filename in episode_files:
            best = await find_best_subtitles(filename, cache=cache)
        ```
    """
    norm = normalizer or default_normalize

    # Parse filename to extract title
    parsed: dict[str, Any]
    if isinstance(filename_or_dict, str):
        parsed = cast(dict[str, Any], anitopy.parse(filename_or_dict) or {})  # type: ignore[misc]
    else:
        parsed = filename_or_dict

    title = str(parsed.get("anime_title", ""))
    if not title:
        return None

    # Build cache key from catalog-matching attributes
    year = str(parsed.get("anime_year", "") or "")
    season = str(parsed.get("anime_season", "") or "")
    cache_key: CacheKey = (norm(title), year, season)

    # Single scoring loop - works for both cache hit and miss
    best_subtitle: Optional[Subtitles] = None
    best_score = 0

    async for subtitle in _iter_title_subtitles(
        parsed, norm, semaphore, cache, cache_key
    ):
        score = subtitle.calculate_fitness(parsed)
        if score > best_score:
            best_score = score
            best_subtitle = subtitle
        elif score == best_score and best_subtitle is not None:
            # Same score - pick the newer one (more recent date)
            if subtitle.date > best_subtitle.date:
                best_subtitle = subtitle

    return best_subtitle
