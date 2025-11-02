from datetime import date

from animesubinfo.parsers import SearchResultsParser

from ...conftest import FIXTURES_DIR


def prepare_search_results_parser(
    fixture_name: str = "ansi_search_results.html",
) -> SearchResultsParser:
    with open(FIXTURES_DIR / fixture_name, "r", encoding="iso-8859-2") as file:
        html_content = file.read()

    parser = SearchResultsParser()
    parser.feed(html_content)
    return parser


def test_search_results_number_of_pages():
    parser = prepare_search_results_parser()

    assert parser.number_of_pages == 5


def test_search_results_first_subtitles():
    parser = prepare_search_results_parser()

    first_subtitles = parser.subtitles_list[0]

    assert first_subtitles.id == 17833
    assert first_subtitles.episode == 1
    assert first_subtitles.to_episode == 1
    assert first_subtitles.original_title == "Higurashi no Naku Koro ni Kai"
    assert first_subtitles.english_title == "Higurashi no Naku Koro ni Kai"
    assert first_subtitles.alt_title == "When They Cry - Higurashi 2"
    assert first_subtitles.date == date(2007, 8, 31)
    assert first_subtitles.format == "Advanced SSA"
    assert first_subtitles.author == "lb333"
    assert first_subtitles.added_by == "lb333"
    assert first_subtitles.size == "27kB"
    assert first_subtitles.description.startswith(
        "...................:::::: Napisy ::::::......................."
    )
    assert first_subtitles.description.endswith(
        "*Dodana wersja z większym outline, żeby lepiej się oglądało na hardach."
    )
    assert first_subtitles.comment_count == 15
    assert first_subtitles.downloaded_times == 4733
    assert first_subtitles.rating.bad == 0
    assert first_subtitles.rating.average == 0
    assert first_subtitles.rating.very_good == 100


def test_search_results_middle_subtitles():
    parser = prepare_search_results_parser()

    middle_subtitles = parser.subtitles_list[5]

    assert middle_subtitles.id == 23531
    assert middle_subtitles.episode == 3
    assert middle_subtitles.to_episode == 3
    assert middle_subtitles.original_title == "Higurashi no Naku Koro ni Kai"
    assert middle_subtitles.english_title == "Higurashi no Naku Koro ni Kai"
    assert middle_subtitles.alt_title == "When They Cry - Higurashi 2"
    assert middle_subtitles.date == date(2008, 8, 3)
    assert middle_subtitles.format == "Advanced SSA"
    assert middle_subtitles.author == "Shizu"
    assert middle_subtitles.added_by == "Naraku_no_Hana"
    assert middle_subtitles.size == "24kB"
    assert middle_subtitles.description.startswith(
        "------------- ~ Napisy by ~ ---------------------"
    )
    assert middle_subtitles.comment_count == 1
    assert middle_subtitles.downloaded_times == 1597
    assert middle_subtitles.rating.bad == 0
    assert middle_subtitles.rating.average == 0
    assert middle_subtitles.rating.very_good == 100


def test_search_results_last_subtitles():
    parser = prepare_search_results_parser()

    last_subtitles = parser.subtitles_list[-1]

    assert last_subtitles.id == 20853
    assert last_subtitles.episode == 20
    assert last_subtitles.to_episode == 20
    assert last_subtitles.original_title == "Higurashi no Naku Koro ni Kai"
    assert last_subtitles.english_title == "Higurashi no Naku Koro ni Kai"
    assert last_subtitles.alt_title == "When They Cry - Higurashi 2"
    assert last_subtitles.date == date(2008, 2, 10)
    assert last_subtitles.format == "Advanced SSA"
    assert last_subtitles.author == "Shizu"
    assert last_subtitles.added_by == "Naraku_no_Hana"
    assert last_subtitles.size == "16kB"
    assert last_subtitles.description.startswith(
        "------------- ~ Napisy by ~ ---------------------"
    )
    assert last_subtitles.comment_count == 11
    assert last_subtitles.downloaded_times == 2951
    assert last_subtitles.rating.bad == 0
    assert last_subtitles.rating.average == 0
    assert last_subtitles.rating.very_good == 100


def test_search_results_uncommon_rating():
    parser = prepare_search_results_parser()

    uncommon_rating_subtitles = next(
        (s for s in parser.subtitles_list if s.id == 19748), None
    )

    assert uncommon_rating_subtitles is not None
    assert uncommon_rating_subtitles.rating.bad == 0
    assert uncommon_rating_subtitles.rating.average == 13
    assert uncommon_rating_subtitles.rating.very_good == 87


def test_search_results_movie():
    parser = prepare_search_results_parser(
        fixture_name="ansi_search_results_movie.html"
    )

    assert parser.number_of_pages == 1
    movie_subtitles = parser.subtitles_list[0]

    assert movie_subtitles.id == 20721
    assert movie_subtitles.episode == 0
    assert movie_subtitles.to_episode == 0
    assert movie_subtitles.original_title == "Evangelion Shin Gekijouban: Jo"
    assert movie_subtitles.english_title == "Evangelion: 1.0 You Are (Not) Alone"
    assert movie_subtitles.alt_title == "Evangelion: 1.11 You Are (Not) Alone"
    assert movie_subtitles.date == date(2008, 2, 2)
    assert movie_subtitles.format == "MicroDVD"
    assert movie_subtitles.author == "koltom"
    assert movie_subtitles.added_by == "koltom"
    assert movie_subtitles.size == "50kB"
    assert movie_subtitles.description == (
        "Napisy do wersji kinowej 600x328 XviD1.2 - 321MB\n"
        "Dodałem synchronizację dla grupy [Zero-Raws] 1h37m57s 720x480"
    )
    assert movie_subtitles.comment_count == 0
    assert movie_subtitles.downloaded_times == 3241
    assert movie_subtitles.rating.bad == 0
    assert movie_subtitles.rating.average == 0
    assert movie_subtitles.rating.very_good == 0


def test_search_results_large_pages_count():
    parser = prepare_search_results_parser(
        fixture_name="ansi_search_results_large_pages_count.html"
    )

    assert parser.number_of_pages == 55
    assert len(parser.subtitles_list) == 30


def test_search_results_pack():
    parser = prepare_search_results_parser(fixture_name="ansi_search_results_pack.html")

    pack_subs = next((s for s in parser.subtitles_list if s.id == 14480), None)

    assert pack_subs is not None
    assert pack_subs.id == 14480
    assert pack_subs.episode == 1
    assert pack_subs.to_episode == 9
    assert pack_subs.original_title == "Shin Seiki Evangelion"
    assert pack_subs.english_title == "Neon Genesis Evangelion"
    assert pack_subs.alt_title == "Neon Genesis Evangelion"
    assert pack_subs.date == date(2006, 12, 9)
    assert pack_subs.format == "SubStationAlpha"
    assert pack_subs.author == "nieznany"
    assert pack_subs.added_by == "barauna"
    assert pack_subs.size == "77kB"
    assert (
        pack_subs.description
        == "Poprawiony timing do wersji *.rmvb, pobranej ze srony realitylapse.com"
    )
    assert pack_subs.comment_count == 0
    assert pack_subs.downloaded_times == 1722
    assert pack_subs.rating.bad == 0
    assert pack_subs.rating.average == 0
    assert pack_subs.rating.very_good == 0


def test_search_results_one_page():
    parser = prepare_search_results_parser(
        fixture_name="ansi_search_results_one_page.html"
    )

    assert parser.number_of_pages == 1
    assert len(parser.subtitles_list) == 14


def test_search_results_blank():
    parser = prepare_search_results_parser(
        fixture_name="ansi_search_results_blank.html"
    )

    assert parser.number_of_pages == 0
    assert len(parser.subtitles_list) == 0


def test_search_results_with_cookie():
    with open(
        FIXTURES_DIR / "ansi_search_results.html", "r", encoding="iso-8859-2"
    ) as file:
        html_content = file.read()

    test_cookie = "test_cookie_value_123"
    parser = SearchResultsParser(ansi_cookie=test_cookie)
    parser.feed(html_content)

    # Verify sh values are stored for parsed subtitles
    assert len(parser.subtitles_list) > 0
    # Check that at least one subtitle has an sh value stored
    first_subtitle = parser.subtitles_list[0]
    sh_value = parser.get_sh_for_id(first_subtitle.id)
    assert sh_value is not None
    assert len(sh_value) > 0
