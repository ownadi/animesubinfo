"""Tests for find_best_subtitles() function."""

import httpx
import pytest
import respx

from animesubinfo.api import find_best_subtitles

from ..conftest import FIXTURES_DIR


@pytest.mark.asyncio
@respx.mock
async def test_find_best_subtitles_with_filename():
    """Test finding best subtitles with a filename using real-world fixtures."""
    # Mock minimal catalog response with link to Higurashi search
    catalog_html = """<html><body>
    <a href="szukaj_old.php?pTitle=org&amp;szukane=Higurashi+no+Naku+Koro+ni+Kai">Higurashi no Naku Koro ni Kai</a>
    </body></html>"""

    respx.get("http://animesub.info/katalog.php?S=h").mock(
        return_value=httpx.Response(200, text=catalog_html)
    )

    # Load real search results fixture
    with open(
        FIXTURES_DIR / "ansi_search_results.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    # Mock all pages (fixture has 5 pages, matches any request with these base params)
    respx.get(
        url__regex=r"http://animesub\.info/szukaj_old\.php.*pTitle=org.*szukane=Higurashi\+no\+Naku\+Koro\+ni\+Kai.*"
    ).mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=test_cookie"},
        )
    )

    # Test with filename that matches "Higurashi no Naku Koro ni Kai" episode 1
    filename = "[Naraku_no_Hana] Higurashi no Naku Koro ni Kai - 01 [ASS].mkv"
    result = await find_best_subtitles(filename)

    assert result is not None
    assert result.original_title == "Higurashi no Naku Koro ni Kai"
    assert result.episode == 1
    # Should match episode 1 subtitle with release group "Naraku_no_Hana" (ID 21684)
    assert result.id == 21684
    assert result.added_by == "Naraku_no_Hana"


@pytest.mark.asyncio
@respx.mock
async def test_find_best_subtitles_with_parsed_dict():
    """Test finding best subtitles with pre-parsed anitopy dict."""
    # Mock catalog response
    catalog_html = """<html><body>
    <a href="szukaj_old.php?pTitle=org&amp;szukane=Platinum+End">Platinum End</a>
    </body></html>"""

    respx.get("http://animesub.info/katalog.php?S=p").mock(
        return_value=httpx.Response(200, text=catalog_html)
    )

    # Load search results fixture
    with open(
        FIXTURES_DIR / "ansi_search_results_one_page.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    respx.get(
        url__regex=r"http://animesub\.info/szukaj_old\.php.*szukane=Platinum\+End.*"
    ).mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=dict_cookie"},
        )
    )

    # Test with pre-parsed dict
    parsed_dict = {
        "anime_title": "Platinum End",
        "episode_number": "1",
    }
    result = await find_best_subtitles(parsed_dict)

    assert result is not None
    assert "Platinum End" in result.original_title


@pytest.mark.asyncio
@respx.mock
async def test_find_best_subtitles_no_catalog_match():
    """Test when title is not found in catalog."""
    # Load real catalog (contains 'E' titles, won't match 'ZZZ...')
    with open(FIXTURES_DIR / "ansi_catalog.html", "r", encoding="iso-8859-2") as f:
        catalog_html = f.read()

    respx.get("http://animesub.info/katalog.php?S=z").mock(
        return_value=httpx.Response(200, text=catalog_html)
    )

    result = await find_best_subtitles("[Group] ZZZ Nonexistent Anime - 01.mkv")
    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_find_best_subtitles_no_search_results():
    """Test when search returns no results using real blank fixture."""
    # Mock minimal catalog response
    catalog_html = """<html><body>
    <a href="szukaj_old.php?pTitle=org&amp;szukane=Empty+Results">Empty Results</a>
    </body></html>"""

    respx.get("http://animesub.info/katalog.php?S=e").mock(
        return_value=httpx.Response(200, text=catalog_html)
    )

    # Load blank search results fixture
    with open(
        FIXTURES_DIR / "ansi_search_results_blank.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    respx.get(
        url__regex=r"http://animesub\.info/szukaj_old\.php.*szukane=Empty\+Results.*"
    ).mock(return_value=httpx.Response(200, text=search_html))

    result = await find_best_subtitles("[Group] Empty Results - 01.mkv")
    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_find_best_subtitles_no_title():
    """Test when filename has no parseable title."""
    # Mock catalog request that might be made
    respx.get(url__regex=r"http://animesub\.info/katalog\.php.*").mock(
        return_value=httpx.Response(200, text="<html><body></body></html>")
    )

    # Test with filename that has no anime title
    result = await find_best_subtitles("random_file.mkv")
    # Should return None since no match in catalog
    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_find_best_subtitles_movie():
    """Test finding best subtitles for a movie file."""
    # Mock catalog response
    catalog_html = """<html><body>
    <a href="szukaj_old.php?pTitle=jp&amp;szukane=Evangelion+Shin+Gekijouban%3A+Jo">Evangelion Shin Gekijouban: Jo</a>
    </body></html>"""

    respx.get("http://animesub.info/katalog.php?S=e").mock(
        return_value=httpx.Response(200, text=catalog_html)
    )

    # Load movie search results fixture
    with open(
        FIXTURES_DIR / "ansi_search_results_movie.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    respx.get(
        url__regex=r"http://animesub\.info/szukaj_old\.php.*szukane=Evangelion.*"
    ).mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=movie_cookie"},
        )
    )

    # Test with movie filename (no episode number)
    filename = "[Group] Evangelion Shin Gekijouban Jo [BD 1080p].mkv"
    result = await find_best_subtitles(filename)

    assert result is not None
    # Movie should have episode=0 and to_episode=0
    assert result.episode == 0
    assert result.to_episode == 0


@pytest.mark.asyncio
@respx.mock
async def test_find_best_subtitles_single_page():
    """Test finding best subtitle with single page of results."""
    # Mock catalog response
    catalog_html = """<html><body>
    <a href="szukaj_old.php?pTitle=en&amp;szukane=Platinum+End">Platinum End</a>
    </body></html>"""

    respx.get("http://animesub.info/katalog.php?S=p").mock(
        return_value=httpx.Response(200, text=catalog_html)
    )

    # Load single-page search results fixture
    with open(
        FIXTURES_DIR / "ansi_search_results_one_page.html", "r", encoding="iso-8859-2"
    ) as f:
        search_html = f.read()

    respx.get(
        url__regex=r"http://animesub\.info/szukaj_old\.php.*szukane=Platinum\+End.*"
    ).mock(
        return_value=httpx.Response(
            200,
            text=search_html,
            headers={"set-cookie": "ansi_sciagnij=single_cookie"},
        )
    )

    # Test with filename
    filename = "[SubsPlease] Platinum End - 01 [1080p].mkv"
    result = await find_best_subtitles(filename)

    assert result is not None
    assert "Platinum End" in result.original_title
    assert result.episode <= 1 <= result.to_episode


@pytest.mark.asyncio
@respx.mock
async def test_find_best_subtitles_catalog_http_error():
    """Test handling of HTTP errors from catalog request."""
    # Mock catalog request that returns 500 error
    respx.get("http://animesub.info/katalog.php?S=t").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    # Should raise HTTPStatusError
    with pytest.raises(httpx.HTTPStatusError):
        await find_best_subtitles("[Group] Test Anime - 01.mkv")


@pytest.mark.asyncio
@respx.mock
async def test_find_best_subtitles_search_http_error():
    """Test handling of HTTP errors from search request."""
    # Mock successful catalog response
    catalog_html = """<html><body>
    <a href="szukaj_old.php?pTitle=org&amp;szukane=Test+Anime">Test Anime</a>
    </body></html>"""

    respx.get("http://animesub.info/katalog.php?S=t").mock(
        return_value=httpx.Response(200, text=catalog_html)
    )

    # Mock search request that returns 500 error
    respx.get(
        url__regex=r"http://animesub\.info/szukaj_old\.php.*szukane=Test\+Anime.*"
    ).mock(return_value=httpx.Response(500, text="Internal Server Error"))

    # Should raise HTTPStatusError
    with pytest.raises(httpx.HTTPStatusError):
        await find_best_subtitles("[Group] Test Anime - 01.mkv")
