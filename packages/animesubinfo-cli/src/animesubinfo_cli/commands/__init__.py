"""CLI commands package."""

from .best import app as best_app
from .download import app as download_app
from .find import app as find_app
from .search import app as search_app

__all__ = ["best_app", "download_app", "find_app", "search_app"]
