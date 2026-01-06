"""Tests for the search command."""

import json
from collections.abc import AsyncGenerator
from datetime import date

from pytest_mock import MockerFixture
from typer.testing import CliRunner

from animesubinfo import SortBy, Subtitles, SubtitlesRating, TitleType
from animesubinfo_cli.cli import app

MOCK_SEARCH = "animesubinfo_cli.commands.search.search"


async def _async_gen_subtitles(
    subtitles: list[Subtitles],
) -> AsyncGenerator[Subtitles, None]:
    """Helper to create async generator from list."""
    for sub in subtitles:
        yield sub


class TestSearchCommand:
    """Tests for the search command."""

    def test_search_no_results(self, mocker: MockerFixture, runner: CliRunner) -> None:
        """Test search with no results."""
        mock_search = mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([]),
        )

        result = runner.invoke(app, ["search", "NonExistentAnime"])

        assert result.exit_code == 0
        assert "No results found" in result.stdout
        mock_search.assert_called_once_with(
            "NonExistentAnime",
            sort_by=None,
            title_type=None,
            page_limit=None,
        )

    def test_search_with_results(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test search returning results."""
        mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test Anime"])

        assert result.exit_code == 0
        assert "12345" in result.stdout
        assert "2024-01-15" in result.stdout
        assert "100" in result.stdout
        assert "Found 1 subtitle(s)" in result.stdout

    def test_search_multiple_results(
        self, mocker: MockerFixture, runner: CliRunner
    ) -> None:
        """Test search returning multiple results."""
        subtitles = [
            Subtitles(
                id=1001,
                episode=1,
                to_episode=1,
                original_title="Anime One",
                english_title="",
                alt_title="",
                date=date(2024, 1, 1),
                format="ass",
                author="Author1",
                added_by="User1",
                size="10 KB",
                description="",
                comment_count=0,
                downloaded_times=50,
                rating=SubtitlesRating(bad=0, average=0, very_good=0),
            ),
            Subtitles(
                id=2002,
                episode=2,
                to_episode=2,
                original_title="Anime Two",
                english_title="",
                alt_title="",
                date=date(2024, 1, 2),
                format="srt",
                author="Author2",
                added_by="User2",
                size="12 KB",
                description="",
                comment_count=0,
                downloaded_times=75,
                rating=SubtitlesRating(bad=0, average=0, very_good=0),
            ),
        ]
        mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles(subtitles),
        )

        result = runner.invoke(app, ["search", "Anime"])

        assert result.exit_code == 0
        # Check IDs are present (table may wrap titles)
        assert "1001" in result.stdout
        assert "2002" in result.stdout
        assert "Found 2 subtitle(s)" in result.stdout

    def test_search_with_sort_option(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test search with sort option."""
        mock_search = mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test", "--sort", "pobrn"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with(
            "Test",
            sort_by=SortBy.DOWNLOADS,
            title_type=None,
            page_limit=None,
        )

    def test_search_with_sort_short_option(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test search with short sort option."""
        mock_search = mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test", "-s", "datad"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with(
            "Test",
            sort_by=SortBy.ADDED_DATE,
            title_type=None,
            page_limit=None,
        )

    def test_search_with_type_option(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test search with title type option."""
        mock_search = mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test", "--type", "en"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with(
            "Test",
            sort_by=None,
            title_type=TitleType.ENGLISH,
            page_limit=None,
        )

    def test_search_with_type_short_option(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test search with short type option."""
        mock_search = mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test", "-t", "org"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with(
            "Test",
            sort_by=None,
            title_type=TitleType.ORIGINAL,
            page_limit=None,
        )

    def test_search_with_limit_option(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test search with page limit option."""
        mock_search = mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test", "--limit", "5"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with(
            "Test",
            sort_by=None,
            title_type=None,
            page_limit=5,
        )

    def test_search_with_limit_short_option(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test search with short limit option."""
        mock_search = mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test", "-l", "3"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with(
            "Test",
            sort_by=None,
            title_type=None,
            page_limit=3,
        )

    def test_search_with_all_options(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test search with all options combined."""
        mock_search = mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_subtitle]),
        )

        result = runner.invoke(
            app,
            [
                "search",
                "Test",
                "--sort",
                "traf",
                "--type",
                "pl",
                "--limit",
                "10",
            ],
        )

        assert result.exit_code == 0
        mock_search.assert_called_once_with(
            "Test",
            sort_by=SortBy.FITNESS,
            title_type=TitleType.ALTERNATIVE,
            page_limit=10,
        )

    def test_search_invalid_sort_option(self, runner: CliRunner) -> None:
        """Test search with invalid sort option."""
        result = runner.invoke(app, ["search", "Test", "--sort", "invalid"])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower()

    def test_search_invalid_type_option(self, runner: CliRunner) -> None:
        """Test search with invalid title type option."""
        result = runner.invoke(app, ["search", "Test", "--type", "invalid"])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower()

    def test_search_invalid_limit_zero(self, runner: CliRunner) -> None:
        """Test search with limit of 0."""
        result = runner.invoke(app, ["search", "Test", "--limit", "0"])

        assert result.exit_code != 0

    def test_search_invalid_limit_negative(self, runner: CliRunner) -> None:
        """Test search with negative limit."""
        result = runner.invoke(app, ["search", "Test", "--limit", "-1"])

        assert result.exit_code != 0

    def test_search_movie_result(
        self, mocker: MockerFixture, runner: CliRunner, sample_movie_subtitle: Subtitles
    ) -> None:
        """Test search displays movie correctly."""
        mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_movie_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test Movie"])

        assert result.exit_code == 0
        assert "Movie" in result.stdout
        assert "67890" in result.stdout

    def test_search_pack_result(
        self, mocker: MockerFixture, runner: CliRunner, sample_pack_subtitle: Subtitles
    ) -> None:
        """Test search displays episode pack correctly."""
        mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_pack_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test Pack"])

        assert result.exit_code == 0
        assert "1-12" in result.stdout
        assert "11111" in result.stdout

    def test_search_case_insensitive_sort(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test sort option is case insensitive."""
        mock_search = mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test", "--sort", "POBRN"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with(
            "Test",
            sort_by=SortBy.DOWNLOADS,
            title_type=None,
            page_limit=None,
        )

    def test_search_case_insensitive_type(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test type option is case insensitive."""
        mock_search = mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test", "--type", "EN"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with(
            "Test",
            sort_by=None,
            title_type=TitleType.ENGLISH,
            page_limit=None,
        )

    def test_search_missing_title_argument(self, runner: CliRunner) -> None:
        """Test search without required title argument."""
        result = runner.invoke(app, ["search"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output


class TestSearchJsonOutput:
    """Tests for search command JSON output."""

    def test_search_json_output(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test search with --json flag."""
        mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 12345
        assert data[0]["original_title"] == "Test Anime"
        assert data[0]["date"] == "2024-01-15"
        assert data[0]["rating"]["very_good"] == 10

    def test_search_json_short_flag(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test search with -j flag."""
        mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([sample_subtitle]),
        )

        result = runner.invoke(app, ["search", "Test", "-j"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data) == 1

    def test_search_json_no_results(
        self, mocker: MockerFixture, runner: CliRunner
    ) -> None:
        """Test search JSON output with no results."""
        mocker.patch(
            MOCK_SEARCH,
            return_value=_async_gen_subtitles([]),
        )

        result = runner.invoke(app, ["search", "Test", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data == []


class TestSearchHelp:
    """Tests for search command help."""

    def test_search_help(self, runner: CliRunner) -> None:
        """Test search --help displays usage information."""
        result = runner.invoke(app, ["search", "--help"])

        assert result.exit_code == 0
        assert "Search for anime subtitles" in result.stdout
        assert "--sort" in result.stdout
        assert "--type" in result.stdout
        assert "--limit" in result.stdout
        assert "--json" in result.stdout

    def test_main_help_shows_search(self, runner: CliRunner) -> None:
        """Test main --help shows search command."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "search" in result.stdout
