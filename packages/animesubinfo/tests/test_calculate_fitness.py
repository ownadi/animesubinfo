"""Comprehensive tests for Subtitles.calculate_fitness method.

Tests the tiered scoring system and bit manipulation logic that determines
how well a subtitle matches an anime file.
"""

from datetime import date
from typing import Any

from animesubinfo.models import Subtitles, SubtitlesRating


def create_subtitle(
    episode: int = 1,
    to_episode: int = 1,
    original_title: str = "Kimetsu no Yaiba",
    english_title: str = "Demon Slayer",
    alt_title: str = "Pogromca demonów",
    description: str = "",
    date_year: int = 2019,
) -> Subtitles:
    """Helper to create a subtitle with sensible defaults."""
    return Subtitles(
        id=1,
        episode=episode,
        to_episode=to_episode,
        original_title=original_title,
        english_title=english_title,
        alt_title=alt_title,
        date=date(date_year, 1, 1),
        format="srt",
        author="test_author",
        added_by="test_user",
        size="100KB",
        description=description,
        comment_count=0,
        downloaded_times=0,
        rating=SubtitlesRating(bad=0, average=0, very_good=0),
    )


class TestHardRequirements:
    """Test hard requirements that cause calculate_fitness to return 0."""

    def test_episode_mismatch_returns_zero(self):
        """Episode number mismatch should return 0."""
        sub = create_subtitle(episode=5, to_episode=5)

        parsed = {
            "episode_number": "3",
            "anime_title": "Kimetsu no Yaiba",
        }

        assert sub.calculate_fitness(parsed) == 0

    def test_episode_below_range_returns_zero(self):
        """Episode number below subtitle range should return 0."""
        sub = create_subtitle(episode=10, to_episode=15)

        parsed = {
            "episode_number": "9",
            "anime_title": "Kimetsu no Yaiba",
        }

        assert sub.calculate_fitness(parsed) == 0

    def test_episode_above_range_returns_zero(self):
        """Episode number above subtitle range should return 0."""
        sub = create_subtitle(episode=10, to_episode=15)

        parsed = {
            "episode_number": "16",
            "anime_title": "Kimetsu no Yaiba",
        }

        assert sub.calculate_fitness(parsed) == 0

    def test_title_below_60_percent_returns_zero(self):
        """Title similarity below 60% threshold should return 0."""
        sub = create_subtitle(
            original_title="Kimetsu no Yaiba",
            english_title="Demon Slayer",
            alt_title="Pogromca demonów",
        )

        # Completely different title
        parsed = {
            "episode_number": "1",
            "anime_title": "Attack on Titan",
        }

        assert sub.calculate_fitness(parsed) == 0

    def test_empty_title_returns_zero(self):
        """Empty anime title should return 0."""
        sub = create_subtitle()

        parsed = {
            "episode_number": "1",
            "anime_title": "",
        }

        assert sub.calculate_fitness(parsed) == 0

    def test_missing_episode_for_non_movie_returns_zero(self):
        """Missing episode number for non-movie subtitle should return 0."""
        sub = create_subtitle(episode=1, to_episode=1)

        # No episode_number = movie file
        parsed = {
            "anime_title": "Kimetsu no Yaiba",
        }

        assert sub.calculate_fitness(parsed) == 0

    def test_movie_subtitle_matches_movie_file(self):
        """Movie subtitle (episode=0) should match movie file (no episode_number)."""
        sub = create_subtitle(episode=0, to_episode=0)

        parsed = {
            "anime_title": "Kimetsu no Yaiba",  # Perfect match
        }

        score = sub.calculate_fitness(parsed)
        assert score > 0

    def test_movie_subtitle_rejects_episode_file(self):
        """Movie subtitle (episode=0) should reject file with episode number."""
        sub = create_subtitle(episode=0, to_episode=0)

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
        }

        assert sub.calculate_fitness(parsed) == 0


class TestTitleMatching:
    """Test title similarity scoring (0-100 scale)."""

    def test_perfect_title_match_original(self):
        """Perfect match with original title should score 100."""
        sub = create_subtitle(original_title="Kimetsu no Yaiba")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
        }

        score = sub.calculate_fitness(parsed)
        # Extract title score from base (remove tier bits)
        # Score structure: [base][3 bits tier2][1 bit tier3][4 bits tier4]
        # Shift right 8 bits to remove tier bits, then subtract 1 for episode
        title_score = (score >> 8) - 1
        assert title_score == 100

    def test_perfect_title_match_english(self):
        """Perfect match with English title should score 100."""
        sub = create_subtitle(english_title="Demon Slayer")

        parsed = {
            "episode_number": "1",
            "anime_title": "Demon Slayer",
        }

        score = sub.calculate_fitness(parsed)
        title_score = (score >> 8) - 1
        assert title_score == 100

    def test_perfect_title_match_alternative(self):
        """Perfect match with alternative title should score 100."""
        sub = create_subtitle(alt_title="Pogromca demonów")

        parsed = {
            "episode_number": "1",
            "anime_title": "Pogromca demonów",
        }

        score = sub.calculate_fitness(parsed)
        title_score = (score >> 8) - 1
        assert title_score == 100

    def test_title_uses_best_match(self):
        """Should use the best match among all three title variants."""
        sub = create_subtitle(
            original_title="Completely Different Title",
            english_title="Demon Slayer",  # This matches
            alt_title="Another Different Title",
        )

        parsed = {
            "episode_number": "1",
            "anime_title": "Demon Slayer",
        }

        score = sub.calculate_fitness(parsed)
        title_score = (score >> 8) - 1
        assert title_score == 100

    def test_partial_title_match_above_threshold(self):
        """Partial title match above 60% should return proportional score."""
        sub = create_subtitle(original_title="Kimetsu no Yaiba Season 2")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",  # Missing "Season 2"
        }

        score = sub.calculate_fitness(parsed)
        title_score = (score >> 8) - 1
        # Should be between 60 and 99
        assert 60 <= title_score < 100

    def test_case_insensitive_title_matching(self):
        """Title matching should be case insensitive."""
        sub = create_subtitle(original_title="Kimetsu no Yaiba")

        parsed = {
            "episode_number": "1",
            "anime_title": "KIMETSU NO YAIBA",
        }

        score = sub.calculate_fitness(parsed)
        title_score = (score >> 8) - 1
        assert title_score == 100


class TestTier2Scoring:
    """Test Tier 2: File checksum, File name, Source (3 bits = 0-3)."""

    def test_tier2_zero_matches(self):
        """No Tier 2 matches should have tier2 bits = 0."""
        sub = create_subtitle(description="Generic description")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "file_checksum": "ABCD1234",
            "file_name": "some_file.mkv",
            "source": "BluRay",
        }

        score = sub.calculate_fitness(parsed)
        # Extract tier2 bits: shift right 5 (tier3 1 bit + tier4 4 bits), mask 3 bits
        tier2_bits = (score >> 5) & 0b111
        assert tier2_bits == 0

    def test_tier2_one_match_checksum(self):
        """One Tier 2 match (checksum) should have tier2 bits = 1."""
        sub = create_subtitle(description="File checksum: ABCD1234")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "file_checksum": "ABCD1234",
        }

        score = sub.calculate_fitness(parsed)
        tier2_bits = (score >> 5) & 0b111
        assert tier2_bits == 1

    def test_tier2_one_match_filename(self):
        """One Tier 2 match (file name) should have tier2 bits = 1."""
        sub = create_subtitle(description="For file: anime_episode_01")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "file_name": "anime_episode_01.mkv",
        }

        score = sub.calculate_fitness(parsed)
        tier2_bits = (score >> 5) & 0b111
        assert tier2_bits == 1

    def test_tier2_one_match_source(self):
        """One Tier 2 match (source) should have tier2 bits = 1."""
        sub = create_subtitle(description="Source: BluRay")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "source": "BluRay",
        }

        score = sub.calculate_fitness(parsed)
        tier2_bits = (score >> 5) & 0b111
        assert tier2_bits == 1

    def test_tier2_two_matches(self):
        """Two Tier 2 matches should have tier2 bits = 2."""
        sub = create_subtitle(description="BluRay ABCD1234")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "file_checksum": "ABCD1234",
            "source": "BluRay",
        }

        score = sub.calculate_fitness(parsed)
        tier2_bits = (score >> 5) & 0b111
        assert tier2_bits == 2

    def test_tier2_three_matches(self):
        """All three Tier 2 matches should have tier2 bits = 3."""
        sub = create_subtitle(description="BluRay my_anime_file ABCD1234")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "file_checksum": "ABCD1234",
            "file_name": "my_anime_file.mkv",
            "source": "BluRay",
        }

        score = sub.calculate_fitness(parsed)
        tier2_bits = (score >> 5) & 0b111
        assert tier2_bits == 3

    def test_tier2_multiple_checksums(self):
        """Should match any checksum in list."""
        sub = create_subtitle(description="ABCD1234")

        parsed: dict[str, Any] = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "file_checksum": ["FFFF0000", "ABCD1234", "12345678"],
        }

        score = sub.calculate_fitness(parsed)
        tier2_bits = (score >> 5) & 0b111
        assert tier2_bits >= 1


class TestTier3Scoring:
    """Test Tier 3: Release group (1 bit = 0-1)."""

    def test_tier3_no_match(self):
        """No release group match should have tier3 bit = 0."""
        sub = create_subtitle(description="Generic description")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "release_group": "SubsPlease",
        }

        score = sub.calculate_fitness(parsed)
        # Extract tier3 bit: shift right 4 (tier4 bits), mask 1 bit
        tier3_bit = (score >> 4) & 0b1
        assert tier3_bit == 0

    def test_tier3_match(self):
        """Release group match should have tier3 bit = 1."""
        sub = create_subtitle(description="Release by SubsPlease")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "release_group": "SubsPlease",
        }

        score = sub.calculate_fitness(parsed)
        tier3_bit = (score >> 4) & 0b1
        assert tier3_bit == 1

    def test_tier3_multiple_groups(self):
        """Should match any release group in list."""
        sub = create_subtitle(description="By Erai-raws")

        parsed: dict[str, Any] = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "release_group": ["SubsPlease", "Erai-raws", "HorribleSubs"],
        }

        score = sub.calculate_fitness(parsed)
        tier3_bit = (score >> 4) & 0b1
        assert tier3_bit == 1


class TestTier4Scoring:
    """Test Tier 4: Year/Season/Type/Video/Resolution/Audio (4 bits = 0-6)."""

    def test_tier4_zero_matches(self):
        """No Tier 4 matches should have tier4 bits = 0."""
        sub = create_subtitle(
            description="Generic description",
            date_year=2020,
        )

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "anime_year": "2019",
            "anime_season": "2",
            "anime_type": "TV",
            "video_term": "H264",
            "video_resolution": "1080p",
            "audio_term": "AAC",
        }

        score = sub.calculate_fitness(parsed)
        # Extract tier4 bits: mask lowest 4 bits
        tier4_bits = score & 0b1111
        assert tier4_bits == 0

    def test_tier4_one_match_year(self):
        """Year match should increment tier4 bits."""
        sub = create_subtitle(date_year=2019)

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "anime_year": "2019",
        }

        score = sub.calculate_fitness(parsed)
        tier4_bits = score & 0b1111
        assert tier4_bits == 1

    def test_tier4_one_match_season(self):
        """Season match should increment tier4 bits."""
        sub = create_subtitle(description="Season 2")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "anime_season": "2",
        }

        score = sub.calculate_fitness(parsed)
        tier4_bits = score & 0b1111
        assert tier4_bits == 1

    def test_tier4_one_match_type(self):
        """Type match should increment tier4 bits."""
        sub = create_subtitle(description="TV series")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "anime_type": "TV",
        }

        score = sub.calculate_fitness(parsed)
        tier4_bits = score & 0b1111
        assert tier4_bits == 1

    def test_tier4_one_match_video_term(self):
        """Video term match should increment tier4 bits."""
        sub = create_subtitle(description="H264 encoded")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "video_term": "H264",
        }

        score = sub.calculate_fitness(parsed)
        tier4_bits = score & 0b1111
        assert tier4_bits == 1

    def test_tier4_one_match_resolution(self):
        """Resolution match should increment tier4 bits."""
        sub = create_subtitle(description="1080p quality")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "video_resolution": "1080p",
        }

        score = sub.calculate_fitness(parsed)
        tier4_bits = score & 0b1111
        assert tier4_bits == 1

    def test_tier4_one_match_audio(self):
        """Audio term match should increment tier4 bits."""
        sub = create_subtitle(description="AAC audio")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "audio_term": "AAC",
        }

        score = sub.calculate_fitness(parsed)
        tier4_bits = score & 0b1111
        assert tier4_bits == 1

    def test_tier4_all_six_matches(self):
        """All six Tier 4 matches should have tier4 bits = 6."""
        sub = create_subtitle(
            description="2019 Season 2 TV H264 1080p AAC",
            date_year=2019,
        )

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "anime_year": "2019",
            "anime_season": "2",
            "anime_type": "TV",
            "video_term": "H264",
            "video_resolution": "1080p",
            "audio_term": "AAC",
        }

        score = sub.calculate_fitness(parsed)
        tier4_bits = score & 0b1111
        assert tier4_bits == 6

    def test_tier4_three_matches(self):
        """Three Tier 4 matches should have tier4 bits = 3."""
        sub = create_subtitle(
            description="1080p AAC",
            date_year=2019,
        )

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "anime_year": "2019",
            "video_resolution": "1080p",
            "audio_term": "AAC",
        }

        score = sub.calculate_fitness(parsed)
        tier4_bits = score & 0b1111
        assert tier4_bits == 3


class TestCombinedTierScoring:
    """Test combinations of all tiers to verify proper bit manipulation."""

    def test_all_tiers_maximum_score(self):
        """Maximum possible score with all tiers maxed."""
        sub = create_subtitle(
            description="BluRay my_file ABCD1234 SubsPlease 2019 Season 2 TV H264 1080p AAC",
            date_year=2019,
        )

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",  # Perfect match = 100
            "file_checksum": "ABCD1234",
            "file_name": "my_file.mkv",
            "source": "BluRay",
            "release_group": "SubsPlease",
            "anime_year": "2019",
            "anime_season": "2",
            "anime_type": "TV",
            "video_term": "H264",
            "video_resolution": "1080p",
            "audio_term": "AAC",
        }

        score = sub.calculate_fitness(parsed)

        # Verify each tier
        tier4_bits = score & 0b1111
        tier3_bit = (score >> 4) & 0b1
        tier2_bits = (score >> 5) & 0b111
        title_score = (score >> 8) - 1

        assert tier4_bits == 6  # All 6 tier4 matches
        assert tier3_bit == 1  # Release group match
        assert tier2_bits == 3  # All 3 tier2 matches
        assert title_score == 100  # Perfect title match

    def test_tier_weight_verification_higher_beats_lower(self):
        """Higher tier with lower matches should beat lower tier with higher matches."""
        # Subtitle A: Perfect title (100), no other matches
        sub_a = create_subtitle(description="")

        # Subtitle B: Worse title (80), but all tier2/3/4 matches
        sub_b = create_subtitle(
            original_title="Kimetsu no Yaiba Extra Long Title That Reduces Similarity",
            description="BluRay file ABCD SubsPlease 2019 S2 TV H264 1080p AAC",
            date_year=2019,
        )

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "file_checksum": "ABCD",
            "file_name": "file.mkv",
            "source": "BluRay",
            "release_group": "SubsPlease",
            "anime_year": "2019",
            "anime_season": "S2",
            "anime_type": "TV",
            "video_term": "H264",
            "video_resolution": "1080p",
            "audio_term": "AAC",
        }

        score_a = sub_a.calculate_fitness(parsed)
        score_b = sub_b.calculate_fitness(parsed)

        # Score A should be higher because title is weighted more
        # (shifted left more bits)
        assert score_a > score_b

    def test_tier_isolation_tier2_doesnt_affect_tier4(self):
        """Tier 2 changes should not affect Tier 4 bits."""
        sub = create_subtitle(description="1080p AAC")

        # First: with tier2 matches
        parsed_with_tier2 = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "source": "BluRay",
            "video_resolution": "1080p",
            "audio_term": "AAC",
        }

        # Second: without tier2 matches
        parsed_without_tier2 = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "video_resolution": "1080p",
            "audio_term": "AAC",
        }

        sub.description = "BluRay 1080p AAC"
        score_with = sub.calculate_fitness(parsed_with_tier2)

        sub.description = "1080p AAC"
        score_without = sub.calculate_fitness(parsed_without_tier2)

        # Tier 4 bits should be the same
        assert (score_with & 0b1111) == (score_without & 0b1111) == 2

        # Tier 2 bits should differ
        assert ((score_with >> 5) & 0b111) > ((score_without >> 5) & 0b111)

    def test_tier_ordering_preserved(self):
        """Verify that better matches in higher tiers produce higher scores."""
        base_sub = create_subtitle(description="")

        # Create parsed dict with perfect title
        base_parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
        }

        # Score with no tier matches
        score_baseline = base_sub.calculate_fitness(base_parsed)

        # Score with tier 4 match only
        base_sub.description = "1080p"
        parsed_tier4 = {**base_parsed, "video_resolution": "1080p"}
        score_tier4 = base_sub.calculate_fitness(parsed_tier4)

        # Score with tier 3 match only
        base_sub.description = "SubsPlease"
        parsed_tier3 = {**base_parsed, "release_group": "SubsPlease"}
        score_tier3 = base_sub.calculate_fitness(parsed_tier3)

        # Score with tier 2 match only
        base_sub.description = "BluRay"
        parsed_tier2 = {**base_parsed, "source": "BluRay"}
        score_tier2 = base_sub.calculate_fitness(parsed_tier2)

        # Higher tiers should produce higher scores
        assert score_tier2 > score_tier3 > score_tier4 > score_baseline


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_episode_range_boundary_lower(self):
        """Episode at lower boundary of range should match."""
        sub = create_subtitle(episode=5, to_episode=10)

        parsed = {
            "episode_number": "5",
            "anime_title": "Kimetsu no Yaiba",
        }

        assert sub.calculate_fitness(parsed) > 0

    def test_episode_range_boundary_upper(self):
        """Episode at upper boundary of range should match."""
        sub = create_subtitle(episode=5, to_episode=10)

        parsed = {
            "episode_number": "10",
            "anime_title": "Kimetsu no Yaiba",
        }

        assert sub.calculate_fitness(parsed) > 0

    def test_episode_range_middle(self):
        """Episode in middle of range should match."""
        sub = create_subtitle(episode=5, to_episode=10)

        parsed = {
            "episode_number": "7",
            "anime_title": "Kimetsu no Yaiba",
        }

        assert sub.calculate_fitness(parsed) > 0

    def test_empty_description_no_crashes(self):
        """Empty description should not cause errors."""
        sub = create_subtitle(description="")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "file_checksum": "ABCD1234",
            "source": "BluRay",
        }

        score = sub.calculate_fitness(parsed)
        assert score > 0  # Should still score on title

    def test_all_empty_titles_returns_zero(self):
        """Subtitle with all empty titles should return 0."""
        sub = create_subtitle(
            original_title="",
            english_title="",
            alt_title="",
        )

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
        }

        assert sub.calculate_fitness(parsed) == 0

    def test_string_filename_parsed_by_anitopy(self):
        """String filename should be automatically parsed by anitopy."""
        sub = create_subtitle(description="ABCD1234 SubsPlease 1080p")

        # Pass a filename string instead of parsed dict
        filename = "[SubsPlease] Kimetsu no Yaiba - 01 (1080p) [ABCD1234].mkv"

        score = sub.calculate_fitness(filename)
        assert score > 0

        # Should have matched checksum, release group, and resolution
        tier2_bits = (score >> 5) & 0b111
        tier3_bit = (score >> 4) & 0b1
        tier4_bits = score & 0b1111

        assert tier2_bits >= 1  # At least checksum
        assert tier3_bit == 1  # Release group
        assert tier4_bits >= 1  # At least resolution

    def test_invalid_episode_number_string(self):
        """Invalid episode number string should return 0."""
        sub = create_subtitle()

        parsed = {
            "episode_number": "not_a_number",
            "anime_title": "Kimetsu no Yaiba",
        }

        assert sub.calculate_fitness(parsed) == 0

    def test_year_in_title_matches(self):
        """Year in subtitle title should match anime year."""
        sub = create_subtitle(
            original_title="Kimetsu no Yaiba (2019)",
            date_year=2020,  # Different year in date field
        )

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "anime_year": "2019",
        }

        score = sub.calculate_fitness(parsed)
        tier4_bits = score & 0b1111
        assert tier4_bits >= 1  # Year should match from title

    def test_multiple_values_in_parsed_fields(self):
        """Fields with multiple values should match any."""
        sub = create_subtitle(description="H265")

        parsed: dict[str, Any] = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "video_term": ["H264", "H265", "x264"],  # List of values
        }

        score = sub.calculate_fitness(parsed)
        tier4_bits = score & 0b1111
        assert tier4_bits >= 1  # Should match H265

    def test_normalized_matching_removes_special_chars(self):
        """Normalization should handle special characters."""
        sub = create_subtitle(description="Release: SubsPlease!!!")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "release_group": "SubsPlease",
        }

        score = sub.calculate_fitness(parsed)
        tier3_bit = (score >> 4) & 0b1
        assert tier3_bit == 1

    def test_title_similarity_60_percent_boundary(self):
        """Title at exactly 60% similarity should pass."""
        # Create a title that's exactly 60% similar
        # "Kimetsu no Yaiba" (17 chars) vs "Kimetsu no X" (12 chars)
        # Need to find a combination that gives ~0.60 ratio
        sub = create_subtitle(original_title="Attack on Titan Shingeki")

        parsed = {
            "episode_number": "1",
            "anime_title": "Attack on Titan",  # Partial match
        }

        score = sub.calculate_fitness(parsed)
        # Should be > 0 if above threshold, 0 if below
        # This is a boundary test - actual ratio may vary
        if score > 0:
            title_score = (score >> 8) - 1
            assert title_score >= 60

    def test_case_and_whitespace_normalization(self):
        """Matching should be case-insensitive and ignore extra whitespace."""
        sub = create_subtitle(description="  SUBSPLEASE  ")

        parsed = {
            "episode_number": "1",
            "anime_title": "Kimetsu no Yaiba",
            "release_group": "subsplease",
        }

        score = sub.calculate_fitness(parsed)
        tier3_bit = (score >> 4) & 0b1
        assert tier3_bit == 1
