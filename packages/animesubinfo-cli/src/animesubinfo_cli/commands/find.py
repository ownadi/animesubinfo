"""Find command for matching subtitles to anime files."""

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer

from animesubinfo import find_best_subtitles

from ..output import (
    JsonOutput,
    add_subtitle_row,
    console,
    create_subtitles_table,
    subtitle_to_dict,
)

app = typer.Typer()


@app.command()
def find(
    file: Annotated[Path, typer.Argument(help="Anime file to find subtitles for")],
    output_json: JsonOutput = False,
) -> None:
    """Find the best matching subtitle for an anime file."""
    asyncio.run(_find_async(file, output_json))


async def _find_async(file: Path, output_json: bool) -> None:
    """Async implementation of find command."""
    filename = file.name
    with console.status(f"[bold green]Searching for best match: {filename}"):
        result = await find_best_subtitles(filename)

    if output_json:
        print(json.dumps(subtitle_to_dict(result) if result else None, indent=2))
        return

    if result is None:
        console.print(f"[yellow]No matching subtitle found for '{filename}'[/yellow]")
        return

    table = create_subtitles_table(f"Best match for: {filename}")
    add_subtitle_row(table, result)
    console.print(table)

    if result.description:
        console.print(f"\n[bold]Description:[/bold]\n{result.description}")
