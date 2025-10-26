from animesubinfo.parsers import CatalogParser


def prepare_parser(
    title: str, fixture_name: str = "ansi_catalog.html"
) -> CatalogParser:
    with open(f"tests/fixtures/{fixture_name}", "r", encoding="iso-8859-2") as file:
        html_content = file.read()

    parser = CatalogParser(title)
    parser.feed(html_content)
    return parser


def test_catalog_parser_regular():
    parser = prepare_parser("Elf Princess Rane")

    assert parser.result == "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"


def test_catalog_parser_alternative_en():
    parser = prepare_parser("Fairy Princess Ren")

    assert parser.result == "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"


def test_catalog_parser_alternative_jp():
    parser = prepare_parser("Yousei Hime Ren")

    assert parser.result == "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"


def test_catalog_parser_no_match():
    parser = prepare_parser("Nonexistent Title")

    assert parser.result is None


def test_catalog_parser_invalid_html():
    parser = prepare_parser(
        "Higurashi no Naku Koro ni Kai ep01", fixture_name="ansi_search_results.html"
    )

    assert parser.result is None


def test_feed_and_get_result_regular():
    with open("tests/fixtures/ansi_catalog.html", "r", encoding="iso-8859-2") as file:
        html_content = file.read()

    parser = CatalogParser("Elf Princess Rane")
    result = parser.feed_and_get_result(html_content)

    assert result == "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"


def test_feed_and_get_result_streaming():
    with open("tests/fixtures/ansi_catalog.html", "r", encoding="iso-8859-2") as file:
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


def test_catalog_parser_fuzzy_match():
    """Test fuzzy matching with >= 0.85 similarity when no exact match is found."""
    parser = prepare_parser("Elf Princess Ren")

    # Should match "Elf Princess Rane" with fuzzy matching (similarity ~0.97)
    assert parser.result == "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"


def test_catalog_parser_fuzzy_match_below_threshold():
    """Test that fuzzy matching doesn't match when similarity is below 0.85."""
    parser = prepare_parser("Elf")

    # "Elf" is too short and won't have >= 0.85 similarity with any title
    assert parser.result is None
