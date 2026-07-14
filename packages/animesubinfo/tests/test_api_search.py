"""Tests for search() function."""

import asyncio
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from animesubinfo.api import _fetch_title_subtitles, search
from animesubinfo.models import SortBy, Subtitles, TitleType


@pytest.mark.asyncio
@respx.mock
async def test_search_single_page(fixtures_dir: Path) -> None:
    """Test search with single page of results using real fixture."""
    # Load single page search results fixture
    with open(
        fixtures_dir / "ansi_search_results_one_page.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    # Mock the search request
    respx.get(
        url__regex=r"http://animesub\.info/szukaj\.php.*szukane=Platinum\+End.*"
    ).mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=test_cookie"},
        )
    )

    # Search for "Platinum End"
    results: list[Subtitles] = []
    async for subtitle in search("Platinum End"):
        results.append(subtitle)

    # Should have results from one page
    assert len(results) > 0
    # Verify at least one result has expected title
    assert any("Platinum End" in r.original_title for r in results)


@pytest.mark.asyncio
@respx.mock
async def test_search_multiple_pages(fixtures_dir: Path) -> None:
    """Test search with multiple pages of results using real fixture."""
    # Load multi-page search results fixture (has 5 pages)
    with open(
        fixtures_dir / "ansi_search_results.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    # Mock all page requests (fixture has 5 pages)
    respx.get(
        url__regex=r"http://animesub\.info/szukaj\.php.*szukane=Higurashi.*"
    ).mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=test_cookie_multi"},
        )
    )

    # Search for "Higurashi"
    results: list[Subtitles] = []
    async for subtitle in search("Higurashi"):
        results.append(subtitle)

    # Should have results from multiple pages
    assert len(results) > 30  # More than one page worth


@pytest.mark.asyncio
@respx.mock
async def test_search_with_sort_by(fixtures_dir: Path) -> None:
    """Test search with sort_by parameter."""
    with open(
        fixtures_dir / "ansi_search_results_one_page.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    # Mock request with specific sort parameter
    route = respx.get(
        url__regex=r"http://animesub\.info/szukaj\.php.*pSortuj=data.*"
    ).mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=sorted_cookie"},
        )
    )

    # Search with sort_by parameter
    results: list[Subtitles] = []
    async for subtitle in search("Test", sort_by=SortBy.ADDED_DATE):
        results.append(subtitle)

    # Verify request was made with correct sort parameter
    assert route.called
    assert "pSortuj=datad" in str(route.calls.last.request.url)


@pytest.mark.asyncio
@respx.mock
async def test_search_with_title_type(fixtures_dir: Path) -> None:
    """Test search with title_type parameter."""
    with open(
        fixtures_dir / "ansi_search_results_one_page.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    # Mock request with specific title type parameter
    route = respx.get(
        url__regex=r"http://animesub\.info/szukaj\.php.*pTitle=en.*"
    ).mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=title_cookie"},
        )
    )

    # Search with title_type parameter
    results: list[Subtitles] = []
    async for subtitle in search("Test", title_type=TitleType.ENGLISH):
        results.append(subtitle)

    # Verify request was made with correct title type parameter
    assert route.called
    assert "pTitle=en" in str(route.calls.last.request.url)


@pytest.mark.asyncio
@respx.mock
async def test_search_with_page_limit(fixtures_dir: Path) -> None:
    """Test search with page_limit parameter."""
    with open(
        fixtures_dir / "ansi_search_results.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    # Mock requests (fixture has 5 pages, but we limit to 2)
    route = respx.get(
        url__regex=r"http://animesub\.info/szukaj\.php.*szukane=LimitTest.*"
    ).mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=limit_cookie"},
        )
    )

    # Search with page limit of 2
    results: list[Subtitles] = []
    async for subtitle in search("LimitTest", page_limit=2):
        results.append(subtitle)

    # Should have results
    assert len(results) > 0
    # Verify exactly 2 HTTP requests were made (page 1 + page 2)
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_search_blank_results(fixtures_dir: Path) -> None:
    """Test search with no results using blank fixture."""
    # Load blank search results fixture
    with open(
        fixtures_dir / "ansi_search_results_blank.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    # Mock the search request
    respx.get(
        url__regex=r"http://animesub\.info/szukaj\.php.*szukane=NoResults.*"
    ).mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=blank_cookie"},
        )
    )

    # Search for non-existent title
    results: list[Subtitles] = []
    async for subtitle in search("NoResults"):
        results.append(subtitle)

    # Should have no results
    assert len(results) == 0


@pytest.mark.asyncio
@respx.mock
async def test_search_movie(fixtures_dir: Path) -> None:
    """Test search for movie results using movie fixture."""
    # Load movie search results fixture
    with open(
        fixtures_dir / "ansi_search_results_movie.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    # Mock the search request
    respx.get(
        url__regex=r"http://animesub\.info/szukaj\.php.*szukane=Evangelion.*"
    ).mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=movie_cookie"},
        )
    )

    # Search for Evangelion movie
    results: list[Subtitles] = []
    async for subtitle in search("Evangelion"):
        results.append(subtitle)

    # Should have results
    assert len(results) > 0
    # Movie subtitles should have episode=0 and to_episode=0
    movie_results = [r for r in results if r.episode == 0 and r.to_episode == 0]
    assert len(movie_results) > 0


@pytest.mark.asyncio
@respx.mock
async def test_search_pack(fixtures_dir: Path) -> None:
    """Test search for pack results (multi-episode) using pack fixture."""
    # Load pack search results fixture
    with open(
        fixtures_dir / "ansi_search_results_pack.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    # Mock the search request
    respx.get(url__regex=r"http://animesub\.info/szukaj\.php.*szukane=Pack.*").mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=pack_cookie"},
        )
    )

    # Search for pack
    results: list[Subtitles] = []
    async for subtitle in search("Pack"):
        results.append(subtitle)

    # Should have results
    assert len(results) > 0
    # Pack subtitles should have to_episode > episode
    pack_results = [r for r in results if r.to_episode > r.episode]
    assert len(pack_results) > 0


@pytest.mark.asyncio
@respx.mock
async def test_search_combined_parameters(fixtures_dir: Path) -> None:
    """Test search with multiple parameters combined."""
    with open(
        fixtures_dir / "ansi_search_results_one_page.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    # Mock request - match any request to szukaj.php (params can be in any order)
    route = respx.get(url__regex=r"http://animesub\.info/szukaj\.php.*").mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=combined_cookie"},
        )
    )

    # Search with all parameters
    results: list[Subtitles] = []
    async for subtitle in search(
        "Combined",
        sort_by=SortBy.FITNESS,
        title_type=TitleType.ORIGINAL,
        page_limit=1,
    ):
        results.append(subtitle)

    # Verify request was made with all parameters
    assert route.called
    request_url = str(route.calls.last.request.url)
    assert "pTitle=org" in request_url
    assert "pSortuj=traf" in request_url
    assert "szukane=Combined" in request_url


@pytest.mark.asyncio
@respx.mock
async def test_search_http_error() -> None:
    """Test search handling of HTTP errors."""
    # Mock request that returns 500 error
    respx.get(url__regex=r"http://animesub\.info/szukaj\.php.*").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    # Search should raise HTTPStatusError
    with pytest.raises(httpx.HTTPStatusError):
        async for _ in search("ErrorTest"):
            pass


@pytest.mark.asyncio
async def test_search_early_close_cancels_pending_pages() -> None:
    """Closing search early cancels and drains outstanding page requests."""
    real_client = httpx.AsyncClient
    result = object()
    page_started = asyncio.Event()
    page_cancelled = asyncio.Event()
    never_complete = asyncio.Event()
    clients: list[httpx.AsyncClient] = []

    class FakeSearchResultsParser:
        def __init__(self, ansi_cookie: str = "") -> None:
            self.subtitles_list = [result]
            self.number_of_pages = 2

        def feed(self, chunk: str) -> None:
            pass

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("od") is not None:
            page_started.set()
            try:
                await never_complete.wait()
            except asyncio.CancelledError:
                page_cancelled.set()
                raise

        return httpx.Response(
            200,
            text="search response",
            headers={"set-cookie": "ansi_sciagnij=test_cookie"},
        )

    def client_factory(**kwargs: object) -> httpx.AsyncClient:
        client = real_client(transport=httpx.MockTransport(handler), **kwargs)
        clients.append(client)
        return client

    with (
        patch("animesubinfo.api.SearchResultsParser", FakeSearchResultsParser),
        patch("animesubinfo.api.httpx.AsyncClient", side_effect=client_factory),
    ):
        results = search("Naruto", semaphore=asyncio.Semaphore(1))
        assert await anext(results) is result
        await asyncio.wait_for(page_started.wait(), timeout=1)
        await asyncio.wait_for(results.aclose(), timeout=1)

    assert page_cancelled.is_set()
    assert len(clients) == 1
    assert clients[0].is_closed


@pytest.mark.asyncio
async def test_search_page_error_does_not_cancel_result_consumer() -> None:
    """A background page error is raised by iteration, not task cancellation."""
    real_client = httpx.AsyncClient
    result = object()
    release_page = asyncio.Event()
    page_returned = asyncio.Event()

    class FakeSearchResultsParser:
        def __init__(self, ansi_cookie: str = "") -> None:
            self.subtitles_list = [result]
            self.number_of_pages = 2

        def feed(self, chunk: str) -> None:
            pass

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("od") is not None:
            await release_page.wait()
            page_returned.set()
            return httpx.Response(500, text="later page failed")

        return httpx.Response(
            200,
            text="search response",
            headers={"set-cookie": "ansi_sciagnij=test_cookie"},
        )

    def client_factory(**kwargs: object) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    with (
        patch("animesubinfo.api.SearchResultsParser", FakeSearchResultsParser),
        patch("animesubinfo.api.httpx.AsyncClient", side_effect=client_factory),
    ):
        results = search("Naruto", semaphore=asyncio.Semaphore(1))
        assert await anext(results) is result

        consumer = asyncio.current_task()
        assert consumer is not None
        cancelling_before = consumer.cancelling()

        release_page.set()
        await asyncio.wait_for(page_returned.wait(), timeout=1)
        await asyncio.sleep(0)

        assert consumer.cancelling() == cancelling_before
        with pytest.raises(httpx.HTTPStatusError):
            await anext(results)


@pytest.mark.asyncio
async def test_title_search_can_close_while_yielding_later_pages() -> None:
    """The internal title iterator also closes cleanly after a later-page yield."""
    real_client = httpx.AsyncClient
    result = object()
    clients: list[httpx.AsyncClient] = []

    class FakeCatalogParser:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def feed_and_get_result(self, chunk: str) -> str:
            return "szukaj_old.php?pTitle=en&szukane=Naruto"

    class FakeSearchResultsParser:
        def __init__(self, ansi_cookie: str = "") -> None:
            self.subtitles_list = [result]
            self.number_of_pages = 2

        def feed(self, chunk: str) -> None:
            pass

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="response",
            headers={"set-cookie": "ansi_sciagnij=test_cookie"},
        )

    def client_factory(**kwargs: object) -> httpx.AsyncClient:
        client = real_client(transport=httpx.MockTransport(handler), **kwargs)
        clients.append(client)
        return client

    with (
        patch("animesubinfo.api.CatalogParser", FakeCatalogParser),
        patch("animesubinfo.api.SearchResultsParser", FakeSearchResultsParser),
        patch("animesubinfo.api.httpx.AsyncClient", side_effect=client_factory),
    ):
        results = _fetch_title_subtitles(
            {"anime_title": "Naruto"}, lambda value: value, asyncio.Semaphore(1)
        )
        assert await anext(results) is result
        assert await anext(results) is result
        await results.aclose()

    assert len(clients) == 1
    assert clients[0].is_closed
