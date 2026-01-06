"""Tests for the best command."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from animesubinfo import ExtractedSubtitle, Subtitles
from animesubinfo_cli.cli import app

MOCK_BEST_FIND = "animesubinfo_cli.commands.best.find_best_subtitles"
MOCK_BEST_DOWNLOAD = "animesubinfo_cli.commands.best.download_and_extract_subtitle"


class TestBestCommand:
    """Tests for the best command."""

    def test_best_success(
        self,
        mocker: MockerFixture,
        runner: CliRunner,
        tmp_path: Path,
        sample_subtitle: Subtitles,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test successful best subtitle download."""
        mocker.patch(
            MOCK_BEST_FIND,
            new_callable=AsyncMock,
            return_value=sample_subtitle,
        )
        mocker.patch(
            MOCK_BEST_DOWNLOAD,
            new_callable=AsyncMock,
            return_value=ExtractedSubtitle("subtitle.ass", b"subtitle content"),
        )
        monkeypatch.chdir(tmp_path)

        # Create a dummy video file path
        video_file = tmp_path / "[SubGroup] Test Anime - 01 [1080p].mkv"
        video_file.touch()

        result = runner.invoke(app, ["best", str(video_file)])

        assert result.exit_code == 0
        assert "Saved:" in result.stdout

        # Check subtitle was saved with video name but subtitle extension
        expected_output = video_file.with_suffix(".ass")
        assert expected_output.exists()
        assert expected_output.read_bytes() == b"subtitle content"

    def test_best_no_match(
        self,
        mocker: MockerFixture,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test best with no matching subtitle."""
        mocker.patch(
            MOCK_BEST_FIND,
            new_callable=AsyncMock,
            return_value=None,
        )

        video_file = tmp_path / "unknown.mkv"
        video_file.touch()

        result = runner.invoke(app, ["best", str(video_file)])

        assert result.exit_code == 1
        assert "No matching subtitle found" in result.stdout

    def test_best_file_not_found(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test best with non-existent file."""
        result = runner.invoke(app, ["best", str(tmp_path / "nonexistent.mkv")])

        assert result.exit_code == 1
        assert "File not found" in result.stdout

    def test_best_preserves_video_name(
        self,
        mocker: MockerFixture,
        runner: CliRunner,
        tmp_path: Path,
        sample_subtitle: Subtitles,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that output file uses video name with subtitle extension."""
        mocker.patch(
            MOCK_BEST_FIND,
            new_callable=AsyncMock,
            return_value=sample_subtitle,
        )
        mocker.patch(
            MOCK_BEST_DOWNLOAD,
            new_callable=AsyncMock,
            return_value=ExtractedSubtitle("random_name.srt", b"srt content"),
        )
        monkeypatch.chdir(tmp_path)

        video_file = tmp_path / "My Movie 2024.mp4"
        video_file.touch()

        result = runner.invoke(app, ["best", str(video_file)])

        assert result.exit_code == 0
        expected_output = tmp_path / "My Movie 2024.srt"
        assert expected_output.exists()
        # Check filename in output (normalize whitespace for wrapped lines)
        assert "My Movie 2024.srt" in result.stdout.replace("\n", "")

    def test_best_shows_subtitle_id(
        self,
        mocker: MockerFixture,
        runner: CliRunner,
        tmp_path: Path,
        sample_subtitle: Subtitles,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that found subtitle ID is displayed."""
        mocker.patch(
            MOCK_BEST_FIND,
            new_callable=AsyncMock,
            return_value=sample_subtitle,
        )
        mocker.patch(
            MOCK_BEST_DOWNLOAD,
            new_callable=AsyncMock,
            return_value=ExtractedSubtitle("sub.ass", b"content"),
        )
        monkeypatch.chdir(tmp_path)

        video_file = tmp_path / "test.mkv"
        video_file.touch()

        result = runner.invoke(app, ["best", str(video_file)])

        assert result.exit_code == 0
        assert "12345" in result.stdout  # sample_subtitle.id

    def test_best_missing_file_argument(self, runner: CliRunner) -> None:
        """Test best without required file argument."""
        result = runner.invoke(app, ["best"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output


class TestBestHelp:
    """Tests for best command help."""

    def test_best_help(self, runner: CliRunner) -> None:
        """Test best --help displays usage information."""
        result = runner.invoke(app, ["best", "--help"])

        assert result.exit_code == 0
        assert "Find and download the best matching subtitle" in result.stdout
        assert "FILE" in result.stdout

    def test_main_help_shows_best(self, runner: CliRunner) -> None:
        """Test main --help shows best command."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "best" in result.stdout
