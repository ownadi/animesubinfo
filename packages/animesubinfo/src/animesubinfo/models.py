from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

import anitopy  # type: ignore[import-untyped]

from .utils import normalize


class TitleType(StrEnum):
    ORIGINAL = "org"
    ENGLISH = "en"
    ALTERNATIVE = "pl"


class SortBy(StrEnum):
    FITNESS = "traf"
    ORIGINAL_TITLE = "t_org"
    ENGLISH_TITLE = "t_ang"
    ALTERNATIVE_TITLE = "t_pol"
    ADDED_DATE = "datad"
    DOWNLOADS = "pobrn"
    AUTHOR = "autor"
    PUBLISHER = "udostep"
    COMMENTS = "il_kom"


@dataclass
class SubtitlesRating:
    bad: int
    average: int
    very_good: int


def _get_parsed_values(parsed: dict[str, Any], key: str) -> list[str]:
    """Extract string values from anitopy parsed result.

    Anitopy can return either a string or a list of strings for some fields.
    This helper normalizes the value to always return a list of strings.
    """
    value: Any = parsed.get(key, "")
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]  # type: ignore[misc]
    return [str(value)]  # type: ignore[arg-type]


@dataclass
class Subtitles:
    id: int
    episode: int
    to_episode: int
    original_title: str
    english_title: str
    alt_title: str
    date: date
    format: str
    author: str
    added_by: str
    size: str
    description: str
    comment_count: int
    downloaded_times: int
    rating: SubtitlesRating

    def calculate_fitness(self, filename_or_dict: str | dict[str, Any]) -> int:
        """Calculate compatibility score between subtitle and anime file.

        Uses tiered scoring to determine how well the subtitle matches
        a given anime file (parsed with anitopy).

        Args:
            filename_or_dict: Either a filename string or anitopy-parsed dict

        Returns:
            Compatibility score (0 = incompatible, higher = better match).
            Returns 0 if episode or title doesn't match (hard requirements).

        Scoring criteria (higher tiers contribute more to score):
            - Tier 1: Title similarity (0-100, minimum 60% required)
            - Tier 2: File checksum, File name (w/o extension), Source (BD/DVD/WEB)
            - Tier 3: Release group
            - Tier 4: Year, Season, Type, Video term, Video resolution, Audio term (each evaluated separately)
        """
        # Parse with anitopy if string
        parsed: dict[str, Any]
        if isinstance(filename_or_dict, str):
            parsed = cast(dict[str, Any], anitopy.parse(filename_or_dict) or {})  # type: ignore[misc]
        else:
            parsed = filename_or_dict

        # HARD REQUIREMENTS - must match or return 0
        episode_num = str(parsed.get("episode_number", ""))
        if not self._match_episode(episode_num):
            return 0

        anime_title = str(parsed.get("anime_title", ""))
        title_matches = self._match_title(anime_title)
        if title_matches == 0:
            return 0

        # Normalize description once and store temporarily
        self._desc_norm = normalize(self.description)

        # Start with base score (title similarity 0-100)
        result = 1 + title_matches  # 1 (episode) + 0-100 (title) = 1-101

        # Tier 2: File checksum, File name, Source
        tier2_count = 0
        if self._match_file_checksum(_get_parsed_values(parsed, "file_checksum")):
            tier2_count += 1
        if self._match_file_name(_get_parsed_values(parsed, "file_name")):
            tier2_count += 1
        if self._match_source(_get_parsed_values(parsed, "source")):
            tier2_count += 1

        result = (result << 3) | tier2_count

        # Tier 3: Release group (1 bit)
        tier3_count = (
            1
            if self._match_release_group(_get_parsed_values(parsed, "release_group"))
            else 0
        )
        result = (result << 1) | tier3_count

        # Tier 4: Year/Season/Type/Video term/Video resolution/Audio term (4 bits)
        tier4_count = 0
        if self._match_year(_get_parsed_values(parsed, "anime_year")):
            tier4_count += 1
        if self._match_season(_get_parsed_values(parsed, "anime_season")):
            tier4_count += 1
        if self._match_type(_get_parsed_values(parsed, "anime_type")):
            tier4_count += 1
        if self._match_video_term(_get_parsed_values(parsed, "video_term")):
            tier4_count += 1
        if self._match_video_resolution(_get_parsed_values(parsed, "video_resolution")):
            tier4_count += 1
        if self._match_audio_term(_get_parsed_values(parsed, "audio_term")):
            tier4_count += 1

        result = (result << 4) | tier4_count

        return result

    def _match_episode(self, episode_num: str) -> bool:
        """Check if episode number is within subtitle's episode range.

        For movies, anitopy doesn't provide episode_number key, so episode_num
        will be empty. In this case, match only if subtitle is also a movie
        (episode=0 and to_episode=0).
        """
        if not episode_num:
            # No episode number = movie file
            # Match only if subtitle is also a movie (episode 0)
            return self.episode == 0 and self.to_episode == 0

        try:
            ep = int(episode_num)
            return self.episode <= ep <= self.to_episode
        except (ValueError, TypeError):
            return False

    def _match_title(self, anime_title: str) -> int:
        """Match anime title against subtitle titles using SequenceMatcher.

        Returns:
            Integer score 0-100 based on highest similarity ratio from 3 title variants.
            Returns 0 if similarity is below 60% threshold (hard requirement).
        """
        if not anime_title:
            return 0

        normalized_anime = normalize(anime_title)

        # Calculate similarity ratios for all 3 title variants
        ratios: list[float] = []
        for title in [self.original_title, self.english_title, self.alt_title]:
            if title:  # Skip empty title fields
                normalized_sub_title = normalize(title)
                ratio = SequenceMatcher(
                    None, normalized_anime, normalized_sub_title
                ).ratio()
                ratios.append(ratio)

        # Take the highest ratio from the 3 variants
        if not ratios:
            return 0

        max_ratio = max(ratios)

        # Hard requirement: minimum 60% similarity
        if max_ratio < 0.60:
            return 0

        # Convert to 0-100 integer scale
        return int(max_ratio * 100)

    def _match_file_checksum(self, file_checksums: list[str]) -> bool:
        """Match file checksum (CRC32) in description or sh field."""
        if not file_checksums:
            return False

        # Check if any checksum matches
        for file_checksum in file_checksums:
            checksum_norm = normalize(file_checksum)
            if checksum_norm in self._desc_norm:
                return True
        return False

    def _match_file_name(self, file_names: list[str]) -> bool:
        """Match file name (without extension) in description."""
        if not file_names:
            return False

        # Check if any filename matches
        for file_name in file_names:
            # Remove extension if present
            file_name_no_ext = Path(file_name).stem
            filename_norm = normalize(file_name_no_ext)
            if filename_norm in self._desc_norm:
                return True
        return False

    def _match_source(self, sources: list[str]) -> bool:
        """Match video source (BD/DVD/WEB/etc.) in description."""
        if not sources:
            return False

        # Check if any source keyword matches
        for source in sources:
            normalized = normalize(source)
            if normalized in self._desc_norm:
                return True
        return False

    def _match_release_group(self, groups: list[str]) -> bool:
        """Match release group in author or description."""
        if not groups:
            return False

        # Check if any release group matches
        for group in groups:
            group_norm = normalize(group)
            if group_norm in self._desc_norm:
                return True
        return False

    def _match_year(self, years: list[str]) -> bool:
        """Match anime year in date or title fields."""
        if not years:
            return False

        # Check if any year matches
        for year in years:
            year_norm = normalize(year)
            # Check date year
            if year_norm == str(self.date.year):
                return True
            # Check all title fields and description
            for field in [
                self.original_title,
                self.english_title,
                self.alt_title,
                self.description,
            ]:
                if year_norm in normalize(field):
                    return True

        return False

    def _match_season(self, seasons: list[str]) -> bool:
        """Match anime season in title or description."""
        if not seasons:
            return False

        # Check if any season matches
        for season in seasons:
            season_norm = normalize(season)
            # Check titles and description
            for field in [
                self.original_title,
                self.english_title,
                self.alt_title,
                self.description,
            ]:
                if season_norm in normalize(field):
                    return True

        return False

    def _match_type(self, anime_types: list[str]) -> bool:
        """Match anime type (Movie/OVA/TV) in title or description."""
        if not anime_types:
            return False

        # Check if any type matches
        for anime_type in anime_types:
            type_norm = normalize(anime_type)
            # Check titles and description
            for field in [
                self.original_title,
                self.english_title,
                self.alt_title,
                self.description,
            ]:
                if type_norm in normalize(field):
                    return True

        return False

    def _match_video_term(self, video_terms: list[str]) -> bool:
        """Match video term in description."""
        if not video_terms:
            return False

        # Check if any video term matches
        for term in video_terms:
            term_norm = normalize(term)
            if term_norm in self._desc_norm:
                return True
        return False

    def _match_video_resolution(self, resolutions: list[str]) -> bool:
        """Match video resolution in description."""
        if not resolutions:
            return False

        # Check if any resolution matches
        for resolution in resolutions:
            res_norm = normalize(resolution)
            if res_norm in self._desc_norm:
                return True
        return False

    def _match_audio_term(self, audio_terms: list[str]) -> bool:
        """Match audio term in description."""
        if not audio_terms:
            return False

        # Check if any audio term matches
        for term in audio_terms:
            term_norm = normalize(term)
            if term_norm in self._desc_norm:
                return True
        return False


__all__ = ["Subtitles", "SubtitlesRating", "SortBy", "TitleType"]
