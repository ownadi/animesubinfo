from html.parser import HTMLParser
from html import unescape
from typing import List, Tuple, Optional, Callable
from difflib import SequenceMatcher

from ..utils import normalize


class CatalogParser(HTMLParser):
    """HTML parser for anime catalog pages that finds matching titles.

    Parses HTML catalog pages to find anime entries matching a given title.
    Supports both primary titles (in link text) and alternative titles
    (listed after the main link with "- " prefix).

    Uses the normalize function by default for title matching, which removes
    spaces, special characters, converts to lowercase, and handles leading zeros.
    A custom normalizer can be provided to override this behavior.

    Returns the search page path for the matched anime title, or None if no match found.

    Example:
        parser = CatalogParser("Elf Princess Rane")
        result = parser.feed_and_get_result(html_content)
        # Returns: "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"
        # This is a search page path that can be used to find subtitles

    With custom normalizer:
        def simple_normalizer(text: str) -> str:
            return text.lower().replace(" ", "")

        parser = CatalogParser("Anime Title", normalizer=simple_normalizer)

    For streaming HTML:
        parser = CatalogParser("Anime Title")
        for chunk in html_chunks:
            result = parser.feed_and_get_result(chunk)
            if result:  # Found match, can stop early
                break
    """

    def __init__(self, title: str, *, normalizer: Callable[[str], str] = normalize):
        super().__init__()
        self._normalizer = normalizer
        self._title = self._normalizer(title)
        self._result: Optional[str] = None
        self._current_link: Optional[str] = None
        self._current_text = ""
        self._in_link = False
        self._found_match = False
        self._best_match: Optional[Tuple[float, str]] = None  # (similarity, link)
        self._in_div = False
        self._div_class: Optional[str] = None

    @property
    def result(self) -> Optional[str]:
        """Get the parsing result"""
        return self._result

    def feed_and_get_result(self, data: str) -> Optional[str]:
        """Feed data and return result if found"""
        self.feed(data)
        return self._result

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag == "a":
            for attr_name, attr_value in attrs:
                if (
                    attr_name == "href"
                    and attr_value
                    and attr_value.startswith("szukaj_old.php")
                ):
                    self._current_link = unescape(attr_value)
                    self._in_link = True
                    self._current_text = ""
                    break
        elif tag == "div":
            self._in_div = True
            self._div_class = None
            for attr_name, attr_value in attrs:
                if attr_name == "class":
                    self._div_class = attr_value
                    break

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_link:
            self._in_link = False
            normalized_text = self._normalizer(self._current_text.strip())
            if normalized_text == self._title:
                self._result = self._current_link
                self._found_match = True
            elif not self._found_match and self._current_link:
                # Calculate similarity for potential fuzzy match
                similarity = SequenceMatcher(None, normalized_text, self._title).ratio()
                if similarity >= 0.85:
                    if self._best_match is None or similarity > self._best_match[0]:
                        self._best_match = (similarity, self._current_link)

        elif tag == "div" and self._in_div:
            self._in_div = False
            # Check if we've reached the end of catalog (Stka class)
            if self._div_class == "Stka" and not self._found_match and self._best_match:
                self._result = self._best_match[1]

    def handle_data(self, data: str) -> None:
        if self._in_link:
            self._current_text += data.strip()

        elif not self._found_match and self._current_link:
            # Check if this is an alternative title line (after the main link)
            stripped_data = data.strip()
            if stripped_data.startswith("- "):
                alt_title = stripped_data[2:]
                normalized_alt_title = self._normalizer(alt_title)
                if normalized_alt_title == self._title:
                    self._result = self._current_link
                    self._found_match = True
                else:
                    # Calculate similarity for alternative title fuzzy match
                    similarity = SequenceMatcher(
                        None, normalized_alt_title, self._title
                    ).ratio()
                    if similarity >= 0.60:
                        if self._best_match is None or similarity > self._best_match[0]:
                            self._best_match = (similarity, self._current_link)
