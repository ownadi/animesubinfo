from html.parser import HTMLParser
from html import unescape
from typing import List, Tuple, Optional, Callable
from difflib import SequenceMatcher

from ..utils import normalize


class CatalogParser(HTMLParser):
    """HTML parser for anime catalog pages that finds matching titles.

    Parses HTML catalog pages to find anime entries matching a given title.
    Supports season and year-aware matching by trying multiple search variants
    against normalized catalog text using fuzzy matching.

    When season is provided, tries these variants against each catalog entry:
    - base title (e.g., "yurucamp")
    - title + season (e.g., "yurucamp3")
    - title + "season" + season (e.g., "yurucampseason3")
    - title + season + "season" (e.g., "yurucamp3season")

    When year is provided, also tries:
    - title + year (e.g., "hunterxhunter2011")

    The best matching score across all variants is used for each catalog entry.

    Example:
        parser = CatalogParser("Elf Princess Rane")
        result = parser.feed_and_get_result(html_content)
        # Returns: "szukaj_old.php?pTitle=en&szukane=Elf+Princess+Rane"

    Season-aware matching:
        parser = CatalogParser("Yuru Camp", season="3")
        result = parser.feed_and_get_result(html_content)
        # Matches "Yuru Camp Season 3" in catalog

    Year-aware matching:
        parser = CatalogParser("Hunter x Hunter", year="2011")
        result = parser.feed_and_get_result(html_content)
        # Matches "Hunter x Hunter (2011)" in catalog
    """

    def __init__(
        self,
        title: str,
        *,
        season: Optional[str] = None,
        year: Optional[str] = None,
        threshold: float = 0.6,
        normalizer: Callable[[str], str] = normalize,
    ):
        super().__init__()
        self._normalizer = normalizer
        self._threshold = threshold
        self._search_variants = self._build_search_variants(title, season, year)
        self._result: Optional[str] = None
        self._current_link: Optional[str] = None
        self._current_text = ""
        self._in_link = False
        self._found_match = False
        self._best_match: Optional[Tuple[float, str]] = None  # (similarity, link)
        self._in_div = False
        self._div_class: Optional[str] = None

    def _build_search_variants(
        self, title: str, season: Optional[str], year: Optional[str]
    ) -> List[str]:
        """Build list of search variants to try against catalog entries.

        When season or year is provided, only season/year-specific variants
        are included (no base title). This prevents the base title from
        "stealing" matches when searching for a specific season/year.

        Each variant is normalized as a complete string to ensure consistency
        with custom normalizers.
        """
        variants: List[str] = []

        if season:
            s = str(season)
            variants.extend(
                [
                    self._normalizer(f"{title} {s}"),
                    self._normalizer(f"{title} Season {s}"),
                    self._normalizer(f"{title} {s} Season"),
                ]
            )

        if year:
            variants.append(self._normalizer(f"{title} {year}"))

        # Only include base variant if no season/year specified
        if not variants:
            variants = [self._normalizer(title)]

        return variants

    @property
    def result(self) -> Optional[str]:
        """Get the parsing result"""
        return self._result

    def feed_and_get_result(self, data: str) -> Optional[str]:
        """Feed data and return result if found"""
        self.feed(data)
        return self._result

    def _calculate_match(self, catalog_text: str) -> Tuple[bool, float]:
        """Calculate best match score for a catalog entry against all search variants.

        Tries all search variants (base title, with season, with year) against
        the normalized catalog text and returns the best score.

        Args:
            catalog_text: The catalog entry text to match against

        Returns:
            Tuple of (is_exact_match, similarity_score).
            Returns (False, 0.0) if below threshold.
        """
        normalized_catalog = self._normalizer(catalog_text)

        best_score = 0.0
        is_exact = False

        for variant in self._search_variants:
            if variant == normalized_catalog:
                return (True, 1.0)  # Exact match, return immediately

            score = SequenceMatcher(None, variant, normalized_catalog).ratio()
            if score > best_score:
                best_score = score

        if best_score >= self._threshold:
            return (is_exact, best_score)

        return (False, 0.0)

    def _extract_search_path(self, href: str) -> Optional[str]:
        """Extract relative search path from href, handling both relative and absolute URLs."""
        # Handle absolute URLs like "http://animesub.info/szukaj_old.php?..."
        prefix = "http://animesub.info/"
        if href.startswith(prefix):
            href = href[len(prefix) :]
        # Only accept szukaj_old.php URLs
        if href.startswith("szukaj_old.php"):
            return unescape(href)
        return None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag == "a":
            for attr_name, attr_value in attrs:
                if attr_name == "href" and attr_value:
                    search_path = self._extract_search_path(attr_value)
                    if search_path:
                        self._current_link = search_path
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
            catalog_text = self._current_text.strip()
            is_exact, similarity = self._calculate_match(catalog_text)

            if is_exact:
                self._result = self._current_link
                self._found_match = True
            elif not self._found_match and self._current_link and similarity > 0:
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
                is_exact, similarity = self._calculate_match(alt_title)

                if is_exact:
                    self._result = self._current_link
                    self._found_match = True
                elif similarity > 0:
                    if self._best_match is None or similarity > self._best_match[0]:
                        self._best_match = (similarity, self._current_link)
