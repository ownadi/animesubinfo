"""Tests for ranked subtitle matching."""

from datetime import date
from unittest.mock import patch

import pytest

from animesubinfo import (
    SubtitleMatch,
    Subtitles,
    SubtitlesRating,
    find_subtitle_matches,
    find_subtitles,
)
from animesubinfo.api import find_best_subtitles


def _subtitle(subtitle_id: int, uploaded: date) -> Subtitles:
    return Subtitles(
        id=subtitle_id,
        episode=1,
        to_episode=1,
        original_title="Test Anime",
        english_title="",
        alt_title="",
        date=uploaded,
        format="ass",
        author="Author",
        added_by="Uploader",
        size="10 KB",
        description="",
        comment_count=0,
        downloaded_times=0,
        rating=SubtitlesRating(bad=0, average=0, very_good=0),
    )


@pytest.mark.asyncio
async def test_find_subtitle_matches_retains_score_and_orders_matches() -> None:
    subtitles = [
        _subtitle(1, date(2025, 1, 1)),
        _subtitle(2, date(2023, 1, 1)),
        _subtitle(3, date(2024, 1, 1)),
        _subtitle(4, date(2026, 1, 1)),
    ]
    scores = {1: 10, 2: 20, 3: 20, 4: 0}

    async def iter_subtitles(*args, **kwargs):
        for subtitle in subtitles:
            yield subtitle

    with (
        patch("animesubinfo.api._iter_title_subtitles", iter_subtitles),
        patch.object(
            Subtitles,
            "calculate_fitness",
            lambda self, parsed: scores[self.id],
        ),
    ):
        result = await find_subtitle_matches(
            {"anime_title": "Test Anime", "episode_number": "1"}
        )

    assert [(match.subtitle.id, match.score) for match in result] == [
        (3, 20),
        (2, 20),
        (1, 10),
    ]


def test_subtitle_match_identifies_probably_synced_results() -> None:
    subtitle = _subtitle(1, date(2025, 1, 1))
    base_score_with_lower_tiers = (101 << 8) | 0b1_1111

    assert not SubtitleMatch(subtitle, base_score_with_lower_tiers).is_probably_synced
    assert SubtitleMatch(
        subtitle, base_score_with_lower_tiers | (1 << 5)
    ).is_probably_synced


@pytest.mark.asyncio
async def test_find_subtitles_unwraps_scored_matches() -> None:
    expected = _subtitle(1, date(2025, 1, 1))
    matches = [SubtitleMatch(subtitle=expected, score=123)]

    with patch(
        "animesubinfo.api.find_subtitle_matches", return_value=matches
    ) as find_matches:
        result = await find_subtitles("Test Anime - 01.mkv")

    assert result == [expected]
    find_matches.assert_awaited_once_with(
        "Test Anime - 01.mkv",
        normalizer=None,
        semaphore=None,
        cache=None,
    )


@pytest.mark.asyncio
async def test_find_subtitles_returns_empty_for_unparseable_filename() -> None:
    assert await find_subtitles({}) == []


@pytest.mark.asyncio
async def test_find_best_subtitles_returns_first_ranked_match() -> None:
    expected = _subtitle(10, date(2025, 1, 1))

    with patch(
        "animesubinfo.api.find_subtitles", return_value=[expected]
    ) as find_matches:
        result = await find_best_subtitles("Test Anime - 01.mkv")

    assert result is expected
    find_matches.assert_awaited_once_with(
        "Test Anime - 01.mkv",
        normalizer=None,
        semaphore=None,
        cache=None,
    )
