"""Tests for the find command."""

import json
from datetime import date
from unittest.mock import AsyncMock

from pytest_mock import MockerFixture
from typer.testing import CliRunner

from animesubinfo import Subtitles, SubtitlesRating
from animesubinfo_cli.cli import app

MOCK_FIND_BEST_SUBTITLES = "animesubinfo_cli.commands.find.find_best_subtitles"


class TestFindCommand:
    """Tests for the find command."""

    def test_find_no_match(self, mocker: MockerFixture, runner: CliRunner) -> None:
        """Test find with no matching subtitle."""
        mock_find = mocker.patch(
            MOCK_FIND_BEST_SUBTITLES,
            new_callable=AsyncMock,
            return_value=None,
        )

        result = runner.invoke(app, ["find", "[SubGroup] Anime - 01 [1080p].mkv"])

        assert result.exit_code == 0
        assert "No matching subtitle found" in result.stdout
        # Path.name extracts just the filename
        mock_find.assert_called_once_with("[SubGroup] Anime - 01 [1080p].mkv")

    def test_find_with_match(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test find returning a match."""
        mock_find = mocker.patch(
            MOCK_FIND_BEST_SUBTITLES,
            new_callable=AsyncMock,
            return_value=sample_subtitle,
        )

        result = runner.invoke(app, ["find", "[SubGroup] Test Anime - 01 [1080p].mkv"])

        assert result.exit_code == 0
        assert "Best match for" in result.stdout
        assert "12345" in result.stdout
        mock_find.assert_called_once_with("[SubGroup] Test Anime - 01 [1080p].mkv")

    def test_find_movie(
        self, mocker: MockerFixture, runner: CliRunner, sample_movie_subtitle: Subtitles
    ) -> None:
        """Test find with movie result."""
        mocker.patch(
            MOCK_FIND_BEST_SUBTITLES,
            new_callable=AsyncMock,
            return_value=sample_movie_subtitle,
        )

        result = runner.invoke(app, ["find", "[SubGroup] Test Movie [BDRip].mkv"])

        assert result.exit_code == 0
        assert "Movie" in result.stdout
        assert "67890" in result.stdout

    def test_find_pack(
        self, mocker: MockerFixture, runner: CliRunner, sample_pack_subtitle: Subtitles
    ) -> None:
        """Test find with pack result."""
        mocker.patch(
            MOCK_FIND_BEST_SUBTITLES,
            new_callable=AsyncMock,
            return_value=sample_pack_subtitle,
        )

        result = runner.invoke(
            app, ["find", "[SubGroup] Test Pack Anime - 05 [1080p].mkv"]
        )

        assert result.exit_code == 0
        assert "1-12" in result.stdout
        assert "11111" in result.stdout

    def test_find_complex_filename(
        self, mocker: MockerFixture, runner: CliRunner
    ) -> None:
        """Test find with complex anime filename."""
        subtitle = Subtitles(
            id=55555,
            episode=10,
            to_episode=10,
            original_title="Complex Anime Title",
            english_title="Complex English",
            alt_title="",
            date=date(2024, 5, 15),
            format="ass",
            author="ComplexAuthor",
            added_by="User",
            size="20 KB",
            description="1080p HEVC",
            comment_count=15,
            downloaded_times=250,
            rating=SubtitlesRating(bad=1, average=3, very_good=15),
        )
        mock_find = mocker.patch(
            MOCK_FIND_BEST_SUBTITLES,
            new_callable=AsyncMock,
            return_value=subtitle,
        )

        complex_filename = (
            "[SubGroup] Complex Anime Title - 10 "
            "[1080p HEVC x265 10bit][FLAC][B5E8A2C1].mkv"
        )
        result = runner.invoke(app, ["find", complex_filename])

        assert result.exit_code == 0
        assert "55555" in result.stdout
        assert "Complex Anime Title" in result.stdout
        mock_find.assert_called_once_with(complex_filename)

    def test_find_missing_filename_argument(self, runner: CliRunner) -> None:
        """Test find without required filename argument."""
        result = runner.invoke(app, ["find"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_find_displays_all_columns(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test find displays all table columns."""
        mocker.patch(
            MOCK_FIND_BEST_SUBTITLES,
            new_callable=AsyncMock,
            return_value=sample_subtitle,
        )

        result = runner.invoke(app, ["find", "[Group] Anime - 01.mkv"])

        assert result.exit_code == 0
        # Check all expected data is present
        assert "12345" in result.stdout  # ID
        assert "1" in result.stdout  # Episode
        assert "2024-01-15" in result.stdout  # Date
        assert "100" in result.stdout  # Downloads


class TestFindJsonOutput:
    """Tests for find command JSON output."""

    def test_find_json_output(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test find with --json flag."""
        mocker.patch(
            MOCK_FIND_BEST_SUBTITLES,
            new_callable=AsyncMock,
            return_value=sample_subtitle,
        )

        result = runner.invoke(app, ["find", "test.mkv", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["id"] == 12345
        assert data["original_title"] == "Test Anime"
        assert data["date"] == "2024-01-15"
        assert data["rating"]["very_good"] == 10

    def test_find_json_short_flag(
        self, mocker: MockerFixture, runner: CliRunner, sample_subtitle: Subtitles
    ) -> None:
        """Test find with -j flag."""
        mocker.patch(
            MOCK_FIND_BEST_SUBTITLES,
            new_callable=AsyncMock,
            return_value=sample_subtitle,
        )

        result = runner.invoke(app, ["find", "test.mkv", "-j"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["id"] == 12345

    def test_find_json_no_match(
        self, mocker: MockerFixture, runner: CliRunner
    ) -> None:
        """Test find JSON output with no match."""
        mocker.patch(
            MOCK_FIND_BEST_SUBTITLES,
            new_callable=AsyncMock,
            return_value=None,
        )

        result = runner.invoke(app, ["find", "test.mkv", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data is None


class TestFindHelp:
    """Tests for find command help."""

    def test_find_help(self, runner: CliRunner) -> None:
        """Test find --help displays usage information."""
        result = runner.invoke(app, ["find", "--help"])

        assert result.exit_code == 0
        assert "Find the best matching subtitle" in result.stdout
        assert "FILE" in result.stdout
        assert "--json" in result.stdout

    def test_main_help_shows_find(self, runner: CliRunner) -> None:
        """Test main --help shows find command."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "find" in result.stdout
