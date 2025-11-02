import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import List, Optional, Tuple, Dict, Sequence

from ..models import Subtitles, SubtitlesRating


class SearchResultsParser(HTMLParser):
    """Parser for search results from AnimeSubInfo website."""

    def __init__(self, ansi_cookie: Optional[str] = None):
        super().__init__()
        self._subtitles_list: List[Subtitles] = []
        self._number_of_pages: int = 0
        self._ansi_cookie: str = ansi_cookie or ""

        # State tracking
        self._in_napisy_table = False
        self._is_header_table = True
        self._current_row = 0
        self._current_col = 0
        self._in_td = False
        self._in_form = False
        self._in_description_td = False
        self._table_depth = 0

        # Current subtitle being processed
        self._current_subs: Optional[Subtitles] = None
        self._desc_parts: List[str] = []
        self._current_sh: str = ""
        self._sh_values: Dict[int, str] = {}

        # Regex patterns
        self._rating_pattern = re.compile(r"background:url\(/pics/(g[123])\.gif\)")
        self._episode_pattern = re.compile(r" ep(\d+)(?:-(\d+))?$")

    def handle_starttag(
        self, tag: str, attrs: Sequence[Tuple[str, str | None]]
    ) -> None:
        attrs_dict: Dict[str, str] = {k: v or "" for k, v in attrs}

        # Track all tables (including nested ones)
        if tag == "table":
            if attrs_dict.get("class") == "Napisy":
                if self._is_header_table:
                    # Skip the header table
                    self._is_header_table = False
                    self._in_napisy_table = False  # Don't process header table
                    self._table_depth = 1
                    self._current_row = 0
                    return
                else:
                    # Start a new subtitle table
                    self._in_napisy_table = True
                    self._table_depth = 1
                    self._current_row = 0
                    self._current_subs = Subtitles(
                        id=0,
                        episode=0,
                        to_episode=0,
                        original_title="",
                        english_title="",
                        alt_title="",
                        date=date.today(),  # Placeholder, will be overwritten
                        format="",
                        author="",
                        added_by="",
                        size="",
                        description="",
                        comment_count=0,
                        downloaded_times=0,
                        rating=SubtitlesRating(bad=0, average=0, very_good=0),
                    )
                    self._current_sh = ""
                    self._desc_parts = []
            elif self._in_napisy_table:
                # Nested table (e.g., rating table)
                self._table_depth += 1

        elif tag == "tr" and self._in_napisy_table:
            self._current_row += 1
            self._current_col = 0
            # Reset description flag for new row
            self._in_description_td = False
            # Check if this is the description row (class KKom)
            if attrs_dict.get("class") == "KKom":
                self._in_description_td = True

        elif tag == "td":
            if self._in_napisy_table:
                self._current_col += 1
                self._in_td = True

                # Handle rating table nested inside td
                if "style" in attrs_dict:
                    style: str = attrs_dict["style"]
                    match = self._rating_pattern.search(style)
                    if match and self._current_subs:
                        rating_type = match.group(1)
                        # Extract the width percentage
                        width_match = re.search(r"width:(\d+)%", style)
                        if width_match:
                            percentage = int(width_match.group(1))
                            if rating_type == "g1":
                                self._current_subs.rating.bad = percentage
                            elif rating_type == "g2":
                                self._current_subs.rating.average = percentage
                            elif rating_type == "g3":
                                self._current_subs.rating.very_good = percentage

        elif tag == "form" and self._in_napisy_table:
            self._in_form = True

        elif tag == "input" and self._in_form and self._current_subs:
            if attrs_dict.get("type") == "hidden":
                name: str = attrs_dict.get("name", "")
                value: str = attrs_dict.get("value", "")
                if name == "id":
                    try:
                        self._current_subs.id = int(value)
                    except ValueError:
                        pass
                elif name == "sh":
                    self._current_sh = value

        # Look for page navigation
        elif tag == "a" and "href" in attrs_dict:
            href: str = attrs_dict["href"]
            if "od=" in href:
                # Extract page number from od= parameter
                try:
                    page_match = re.search(r"od=(\d+)", href)
                    if page_match:
                        page_num = (
                            int(page_match.group(1)) + 1
                        )  # od is 0-based, pages are 1-based
                        self._number_of_pages = max(
                            max(self._number_of_pages, 1), page_num
                        )
                except ValueError:
                    pass

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            if self._in_napisy_table:
                self._table_depth -= 1
                if self._table_depth == 0:
                    # End of main napisy table
                    self._in_napisy_table = False
                    if self._current_subs and self._current_subs.id != 0:
                        # Complete the subtitle
                        self._current_subs.description = "\n".join(
                            self._desc_parts
                        ).strip()
                        self._subtitles_list.append(self._current_subs)
                        # Store sh value for this subtitle id
                        if self._current_sh:
                            self._sh_values[self._current_subs.id] = self._current_sh
                        # If we have results, there's at least 1 page
                        if self._number_of_pages == 0:
                            self._number_of_pages = 1
                    self._current_subs = None
                    self._desc_parts = []
                    self._in_description_td = False
                    self._current_sh = ""
            elif self._table_depth > 0:
                self._table_depth -= 1

        elif tag == "form":
            self._in_form = False

        elif tag == "td":
            self._in_td = False
            # Don't reset _in_description_td here - it should persist for the entire KKom row

    def handle_data(self, data: str) -> None:
        data = data.strip()
        if not data:
            return

        if self._in_napisy_table and self._in_td and self._current_subs:
            if self._in_description_td and self._current_row == 5:
                # Handle description content in the 5th row
                if data.startswith("ID "):
                    # This is the start of the description - skip it
                    pass
                elif data == "Autor:":
                    # Next data item will be the author
                    self._waiting_for_author = True
                elif hasattr(self, "_waiting_for_author") and self._waiting_for_author:
                    # This is the author
                    self._current_subs.author = data
                    self._waiting_for_author = False
                else:
                    # Regular description content
                    self._desc_parts.append(data)
            else:
                # Handle regular table cells based on row and column
                if self._current_row == 1:  # First data row
                    if self._current_col == 1:  # Original title
                        title, episode, to_episode = self._extract_title_and_episode(
                            data
                        )
                        self._current_subs.original_title = title
                        self._current_subs.episode = episode
                        self._current_subs.to_episode = to_episode
                    elif self._current_col == 2:  # Date
                        try:
                            # Parse date in format YYYY.MM.DD
                            self._current_subs.date = datetime.strptime(
                                data, "%Y.%m.%d"
                            ).date()
                        except ValueError:
                            # If parsing fails, keep the placeholder date
                            pass
                    elif self._current_col == 4:  # Format
                        self._current_subs.format = data

                elif self._current_row == 2:  # Second data row
                    if self._current_col == 1:  # English title
                        title, _, _ = self._extract_title_and_episode(data)
                        self._current_subs.english_title = title
                    elif self._current_col == 2 and data.startswith("~"):  # Added by
                        self._current_subs.added_by = data[1:]

                elif self._current_row == 3:  # Third data row (size only)
                    if self._current_col == 2:  # Size
                        self._current_subs.size = data

                elif self._current_row == 4:  # Fourth data row
                    if self._current_col == 1:  # Alt title
                        title, _, _ = self._extract_title_and_episode(data)
                        self._current_subs.alt_title = title
                    elif (
                        self._current_col == 2
                        and data.startswith("(")
                        and data.endswith(")")
                    ):  # Comment count
                        try:
                            self._current_subs.comment_count = int(data[1:-1])
                        except ValueError:
                            pass
                    elif self._current_col == 4 and "razy" in data:  # Downloaded times
                        try:
                            self._current_subs.downloaded_times = int(data.split()[0])
                        except (ValueError, IndexError):
                            pass

        # Parse page numbers from text content
        elif data.isdigit() and not self._in_napisy_table:
            try:
                page_num = int(data)
                if page_num > 1:  # Only consider reasonable page numbers
                    self._number_of_pages = max(max(self._number_of_pages, 1), page_num)
            except ValueError:
                pass

    def _extract_title_and_episode(self, title: str) -> Tuple[str, int, int]:
        """Extract title and episode numbers from title string."""
        match = self._episode_pattern.search(title)
        if match:
            base_title = title[: match.start()]
            episode = int(match.group(1))
            to_episode = int(match.group(2)) if match.group(2) else episode
            return base_title, episode, to_episode
        else:
            return title, 0, 0

    @property
    def subtitles_list(self) -> List[Subtitles]:
        """Get the list of parsed subtitles."""
        return self._subtitles_list

    @property
    def number_of_pages(self) -> int:
        """Get the number of pages found in search results."""
        return self._number_of_pages

    def get_sh_for_id(self, subtitle_id: int) -> Optional[str]:
        """Get the sh value for a specific subtitle id."""
        return self._sh_values.get(subtitle_id)
