from pathlib import Path

from animesubinfo.parsers import CatalogParser


def prepare_parser(
    fixtures_dir: Path, title: str, fixture_name: str = "ansi_catalog.html"
) -> CatalogParser:
    with open(fixtures_dir / fixture_name, "r", encoding="iso-8859-2") as file:
        html_content = file.read()

    parser = CatalogParser(title)
    parser.feed(html_content)
    return parser


def prepare_parser_with_params(
    fixtures_dir: Path,
    title: str,
    fixture_name: str = "ansi_catalog.html",
    season: str | None = None,
    year: str | None = None,
) -> CatalogParser:
    """Prepare a CatalogParser with season/year parameters."""
    with open(fixtures_dir / fixture_name, "r", encoding="iso-8859-2") as file:
        html_content = file.read()

    parser = CatalogParser(title, season=season, year=year)
    parser.feed(html_content)
    return parser


def test_catalog_parser_regular(fixtures_dir: Path):
    parser = prepare_parser(fixtures_dir, "Elf Princess Rane")

    assert parser.result == "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"


def test_catalog_parser_alternative_en(fixtures_dir: Path):
    parser = prepare_parser(fixtures_dir, "Fairy Princess Ren")

    assert parser.result == "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"


def test_catalog_parser_alternative_jp(fixtures_dir: Path):
    parser = prepare_parser(fixtures_dir, "Yousei Hime Ren")

    assert parser.result == "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"


def test_catalog_parser_no_match(fixtures_dir: Path):
    parser = prepare_parser(fixtures_dir, "Nonexistent Title")

    assert parser.result is None


def test_catalog_parser_invalid_html(fixtures_dir: Path):
    parser = prepare_parser(
        fixtures_dir,
        "Higurashi no Naku Koro ni Kai ep01",
        fixture_name="ansi_search_results.html",
    )

    assert parser.result is None


def test_feed_and_get_result_regular(fixtures_dir: Path):
    with open(fixtures_dir / "ansi_catalog.html", "r", encoding="iso-8859-2") as file:
        html_content = file.read()

    parser = CatalogParser("Elf Princess Rane")
    result = parser.feed_and_get_result(html_content)

    assert result == "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"


def test_feed_and_get_result_streaming(fixtures_dir: Path):
    with open(fixtures_dir / "ansi_catalog.html", "r", encoding="iso-8859-2") as file:
        html_content = file.read()

    parser = CatalogParser("Elf Princess Rane")

    # Split content into chunks and feed progressively
    chunk_size = 1000
    result = None
    for i in range(0, len(html_content), chunk_size):
        chunk = html_content[i : i + chunk_size]
        result = parser.feed_and_get_result(chunk)
        if result:  # Found match, can stop early
            break

    assert result == "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"


def test_catalog_parser_fuzzy_match(fixtures_dir: Path):
    """Test fuzzy matching with >= 0.6 similarity when no exact match is found."""
    parser = prepare_parser(fixtures_dir, "Elf Princess Ren")

    # Should match "Elf Princess Rane" with fuzzy matching (similarity ~0.97)
    assert parser.result == "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"


def test_catalog_parser_fuzzy_match_below_threshold(fixtures_dir: Path):
    """Test that fuzzy matching doesn't match when similarity is below 0.6."""
    parser = prepare_parser(fixtures_dir, "Elf")

    # "Elf" is too short and won't have >= 0.6 similarity with any title
    assert parser.result is None


# Yuru Camp season/movie matching tests using ansi_catalog_y.html fixture


def test_catalog_yuru_camp_season_3(fixtures_dir: Path):
    """Test that 'Yuru Camp' with season=3 matches 'Yuru Camp Season 3' in catalog."""
    parser = prepare_parser_with_params(
        fixtures_dir, "Yuru Camp", fixture_name="ansi_catalog_y.html", season="3"
    )

    # Should match "Yuru Camp Season 3" via variant matching
    assert parser.result == "szukaj_old.php?pTitle=jp&szukane=Yuru+Camp+Season+3"


def test_catalog_yuru_camp_season_2(fixtures_dir: Path):
    """Test that 'Yuru Camp' with season=2 matches 'Yuru Camp Season 2' in catalog."""
    parser = prepare_parser_with_params(
        fixtures_dir, "Yuru Camp", fixture_name="ansi_catalog_y.html", season="2"
    )

    # Should match "Yuru Camp Season 2" via variant matching
    assert parser.result == "szukaj_old.php?pTitle=jp&szukane=Yuru+Camp+Season+2"


def test_catalog_yuru_camp_base(fixtures_dir: Path):
    """Test that 'Yuru Camp' without season matches base catalog entry."""
    parser = prepare_parser_with_params(
        fixtures_dir, "Yuru Camp", fixture_name="ansi_catalog_y.html"
    )

    # Should match "Yuru Camp" exactly
    assert parser.result == "szukaj_old.php?pTitle=jp&szukane=Yuru+Camp"


def test_catalog_yuru_camp_movie_fuzzy(fixtures_dir: Path):
    """Test that 'Yuru Camp Movie' fuzzy-matches 'Yuru Camp The Movie'."""
    # No type filtering - just fuzzy matching on normalized text
    parser = prepare_parser_with_params(
        fixtures_dir, "Yuru Camp Movie", fixture_name="ansi_catalog_y.html"
    )

    # Should fuzzy-match "Yuru Camp The Movie" (similarity ~0.897)
    assert parser.result == "szukaj_old.php?pTitle=jp&szukane=Yuru+Camp+The+Movie"


def test_catalog_season_format_s3(fixtures_dir: Path):
    """Test that season=3 matches various catalog formats (Season 3, S3, etc)."""
    parser = prepare_parser_with_params(
        fixtures_dir, "Yuru Camp", fixture_name="ansi_catalog_y.html", season="3"
    )

    # Catalog has "Yuru Camp Season 3", our variants include "yurucampseason3"
    assert parser.result == "szukaj_old.php?pTitle=jp&szukane=Yuru+Camp+Season+3"


# Bakuman tests - sequel number matching (not detected as season by anitopy)


def test_catalog_bakuman_base(fixtures_dir: Path):
    """Test that 'Bakuman' matches 'Bakuman.' in catalog."""
    parser = prepare_parser(fixtures_dir, "Bakuman", fixture_name="ansi_catalog_b.html")

    # Should match "Bakuman." exactly (both normalize to "bakuman")
    assert parser.result == "szukaj_old.php?pTitle=en&szukane=Bakuman_"


def test_catalog_bakuman_ii_matches_sequel(fixtures_dir: Path):
    """Test that 'Bakuman II' matches 'Bakuman. 2' via Roman numeral normalization."""
    # "Bakuman II" normalizes to "bakuman2", "Bakuman. 2" also normalizes to "bakuman2"
    parser = prepare_parser(
        fixtures_dir, "Bakuman II", fixture_name="ansi_catalog_b.html"
    )

    # Should match "Bakuman. 2" (alternative title matches)
    assert parser.result == "szukaj_old.php?pTitle=pl&szukane=Bakuman_+2"
