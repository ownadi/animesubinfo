"""Search command for finding anime subtitles."""

import asyncio
import json
from typing import Annotated, Optional

import typer

from animesubinfo import SortBy, Subtitles, TitleType, search

from ..output import (
    JsonOutput,
    add_subtitle_row,
    console,
    create_subtitles_table,
    subtitle_to_dict,
)

app = typer.Typer()


@app.command("search")
def search_cmd(
    title: Annotated[str, typer.Argument(help="Anime title to search for")],
    sort_by: Annotated[
        Optional[SortBy],
        typer.Option(
            "--sort",
            "-s",
            help="Sort results by specified field",
            case_sensitive=False,
        ),
    ] = None,
    title_type: Annotated[
        Optional[TitleType],
        typer.Option(
            "--type",
            "-t",
            help="Filter by title type",
            case_sensitive=False,
        ),
    ] = None,
    limit: Annotated[
        Optional[int],
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of pages to fetch",
            min=1,
        ),
    ] = None,
    output_json: JsonOutput = False,
) -> None:
    """Search for anime subtitles by title."""
    asyncio.run(_search_async(title, sort_by, title_type, limit, output_json))


async def _search_async(
    title: str,
    sort_by: Optional[SortBy],
    title_type: Optional[TitleType],
    limit: Optional[int],
    output_json: bool,
) -> None:
    """Async implementation of search command."""
    results: list[Subtitles] = []
    table = None if output_json else create_subtitles_table(f"Search results for: {title}")
    count = 0

    with console.status(f"[bold green]Searching for: {title}"):
        async for sub in search(
            title,
            sort_by=sort_by,
            title_type=title_type,
            page_limit=limit,
        ):
            if output_json:
                results.append(sub)
            else:
                add_subtitle_row(table, sub)
            count += 1

    if output_json:
        print(json.dumps([subtitle_to_dict(sub) for sub in results], indent=2))
    elif count == 0:
        console.print(f"[yellow]No results found for '{title}'[/yellow]")
    else:
        console.print(table)
        console.print(f"\n[green]Found {count} subtitle(s)[/green]")
