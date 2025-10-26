# pyright: basic
# type: ignore
from .api import (  # noqa: E402
    download_and_extract_subtitle,
    download_subtitles,
    ExtractedSubtitle,
    find_best_subtitles,
    search,
)
from .exceptions import SecurityError, SessionDataError  # noqa: E402
from .models import SortBy, Subtitles, SubtitlesRating, TitleType  # noqa: E402

import anitopy.keyword as keyword_module

keyword_manager = keyword_module.KeywordManager()

keyword_manager.add(
    keyword_module.ElementCategory.SOURCE,
    keyword_module.KeywordOption(),
    ["WEBDL", "WEB-DL", "AMZN", "CR", "Crunchyroll", "N1ETFLIX", "NF"],
)

keyword_manager.add(
    keyword_module.ElementCategory.SOURCE,
    keyword_module.KeywordOption(identifiable=False),
    ["WEB"],
)

import anitopy  # noqa: E402
import anitopy.tokenizer  # noqa: E402
import anitopy.parser  # noqa: E402

anitopy.keyword_manager = keyword_manager
anitopy.keyword.keyword_manager = keyword_manager
anitopy.tokenizer.keyword_manager = keyword_manager
anitopy.parser.keyword_manager = keyword_manager

__all__ = [
    "search",
    "find_best_subtitles",
    "download_subtitles",
    "download_and_extract_subtitle",
    "ExtractedSubtitle",
    "Subtitles",
    "SubtitlesRating",
    "SortBy",
    "TitleType",
    "SecurityError",
    "SessionDataError",
]
