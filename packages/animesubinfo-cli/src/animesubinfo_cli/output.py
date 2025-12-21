"""Shared output utilities for CLI commands."""

from dataclasses import asdict
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from animesubinfo import Subtitles

JsonOutput = Annotated[
    bool,
    typer.Option(
        "--json",
        "-j",
        help="Output results as JSON",
    ),
]

console = Console()


def subtitle_to_dict(sub: Subtitles) -> dict[str, Any]:
    """Convert subtitle to JSON-serializable dict."""
    data = asdict(sub)
    data["date"] = sub.date.isoformat()
    return data


def create_subtitles_table(title: str) -> Table:
    """Create a table for displaying subtitle results."""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Episode", width=10)
    table.add_column("Title", max_width=40)
    table.add_column("Author", max_width=15)
    table.add_column("Date", width=12)
    table.add_column("Downloads", width=10, justify="right")
    return table


def format_episode(sub: Subtitles) -> str:
    """Format episode range."""
    if sub.episode == 0 and sub.to_episode == 0:
        return "Movie"
    if sub.episode == sub.to_episode:
        return str(sub.episode)
    return f"{sub.episode}-{sub.to_episode}"


def format_titles(sub: Subtitles) -> str:
    """Format titles with colors, avoiding duplicates."""
    titles: list[str] = []
    seen: set[str] = set()

    if sub.original_title:
        titles.append(f"[white]{sub.original_title}[/white]")
        seen.add(sub.original_title.lower())

    if sub.english_title and sub.english_title.lower() not in seen:
        titles.append(f"[cyan]{sub.english_title}[/cyan]")
        seen.add(sub.english_title.lower())

    if sub.alt_title and sub.alt_title.lower() not in seen:
        titles.append(f"[red]{sub.alt_title}[/red]")

    return "\n".join(titles) if titles else "-"


def add_subtitle_row(table: Table | None, sub: Subtitles) -> None:
    """Add a subtitle entry to the table."""
    if table is None:
        return
    table.add_row(
        str(sub.id),
        format_episode(sub),
        format_titles(sub),
        sub.author[:15] if sub.author else "-",
        sub.date.isoformat(),
        str(sub.downloaded_times),
    )
