"""Shared test fixtures for animesubinfo-cli tests."""

from datetime import date

import pytest
from typer.testing import CliRunner

from animesubinfo import Subtitles, SubtitlesRating

# Shared runner with colors disabled for consistent CI output
runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})

# Mock target paths
MOCK_SEARCH = "animesubinfo_cli.commands.search.search"
MOCK_FIND_BEST_SUBTITLES = "animesubinfo_cli.commands.find.find_best_subtitles"
MOCK_DOWNLOAD_SUBTITLES = "animesubinfo_cli.commands.download.download_subtitles"
MOCK_BEST_FIND = "animesubinfo_cli.commands.best.find_best_subtitles"
MOCK_BEST_DOWNLOAD = "animesubinfo_cli.commands.best.download_and_extract_subtitle"


@pytest.fixture
def sample_subtitle() -> Subtitles:
    """Create a sample subtitle for testing."""
    return Subtitles(
        id=12345,
        episode=1,
        to_episode=1,
        original_title="Test Anime",
        english_title="Test Anime English",
        alt_title="Test Anime Alt",
        date=date(2024, 1, 15),
        format="ass",
        author="TestAuthor",
        added_by="TestUser",
        size="15 KB",
        description="Test description",
        comment_count=5,
        downloaded_times=100,
        rating=SubtitlesRating(bad=1, average=2, very_good=10),
    )


@pytest.fixture
def sample_movie_subtitle() -> Subtitles:
    """Create a sample movie subtitle for testing."""
    return Subtitles(
        id=67890,
        episode=0,
        to_episode=0,
        original_title="Test Movie",
        english_title="Test Movie English",
        alt_title="",
        date=date(2024, 2, 20),
        format="srt",
        author="MovieAuthor",
        added_by="MovieUser",
        size="25 KB",
        description="Movie description",
        comment_count=10,
        downloaded_times=500,
        rating=SubtitlesRating(bad=0, average=1, very_good=20),
    )


@pytest.fixture
def sample_pack_subtitle() -> Subtitles:
    """Create a sample pack subtitle (multiple episodes) for testing."""
    return Subtitles(
        id=11111,
        episode=1,
        to_episode=12,
        original_title="Test Pack Anime",
        english_title="Test Pack English",
        alt_title="",
        date=date(2024, 3, 10),
        format="ass",
        author="PackAuthor",
        added_by="PackUser",
        size="150 KB",
        description="Episodes 1-12 pack",
        comment_count=25,
        downloaded_times=1000,
        rating=SubtitlesRating(bad=2, average=5, very_good=50),
    )
