"""Tests for the download command."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import pytest
from pytest_mock import MockerFixture

from animesubinfo_cli.cli import app
from conftest import MOCK_DOWNLOAD_SUBTITLES, runner


class MockDownloadResult:
    """Mock for DownloadResult."""

    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self.content_length = len(content)
        self._content = content

    async def _content_iter(self) -> AsyncIterator[bytes]:
        yield self._content

    @property
    def content(self) -> AsyncIterator[bytes]:
        return self._content_iter()


class TestDownloadCommand:
    """Tests for the download command."""

    def test_download_success(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test successful download."""

        @asynccontextmanager
        async def mock_download(_: int) -> AsyncIterator[MockDownloadResult]:
            yield MockDownloadResult("test_subtitle.zip", b"fake zip content")

        mocker.patch(MOCK_DOWNLOAD_SUBTITLES, side_effect=mock_download)

        result = runner.invoke(
            app, ["download", "12345", "-o", str(tmp_path / "output.zip")]
        )

        assert result.exit_code == 0
        assert "Downloaded:" in result.stdout
        assert (tmp_path / "output.zip").exists()
        assert (tmp_path / "output.zip").read_bytes() == b"fake zip content"

    def test_download_uses_original_filename(
        self, mocker: MockerFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test download uses original filename when no output specified."""

        @asynccontextmanager
        async def mock_download(_: int) -> AsyncIterator[MockDownloadResult]:
            yield MockDownloadResult("original_name.zip", b"content")

        mocker.patch(MOCK_DOWNLOAD_SUBTITLES, side_effect=mock_download)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["download", "12345"])

        assert result.exit_code == 0
        assert "original_name.zip" in result.stdout
        assert (tmp_path / "original_name.zip").exists()

    def test_download_with_output_path(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test download with custom output path."""

        @asynccontextmanager
        async def mock_download(_: int) -> AsyncIterator[MockDownloadResult]:
            yield MockDownloadResult("server_name.zip", b"data")

        mocker.patch(MOCK_DOWNLOAD_SUBTITLES, side_effect=mock_download)

        custom_path = tmp_path / "custom" / "path.zip"
        custom_path.parent.mkdir(parents=True)

        result = runner.invoke(app, ["download", "99999", "-o", str(custom_path)])

        assert result.exit_code == 0
        assert custom_path.exists()
        assert custom_path.read_bytes() == b"data"

    def test_download_missing_id_argument(self) -> None:
        """Test download without required ID argument."""
        result = runner.invoke(app, ["download"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output


class TestDownloadHelp:
    """Tests for download command help."""

    def test_download_help(self) -> None:
        """Test download --help displays usage information."""
        result = runner.invoke(app, ["download", "--help"])

        assert result.exit_code == 0
        assert "Download a subtitle file" in result.stdout
        assert "SUBTITLE_ID" in result.stdout
        assert "--output" in result.stdout

    def test_main_help_shows_download(self) -> None:
        """Test main --help shows download command."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "download" in result.stdout
