"""Best command for finding and downloading the best matching subtitle."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from animesubinfo import download_and_extract_subtitle, find_best_subtitles

from ..output import console

app = typer.Typer()


@app.command()
def best(
    file: Annotated[Path, typer.Argument(help="Video file to find subtitles for")],
) -> None:
    """Find and download the best matching subtitle for a video file."""
    asyncio.run(_best_async(file))


async def _best_async(file: Path) -> None:
    """Async implementation of best command."""
    filename = file.name

    with console.status(f"[bold green]Finding best subtitle for: {filename}"):
        subtitle = await find_best_subtitles(filename)

    if subtitle is None:
        console.print(f"[yellow]No matching subtitle found for '{filename}'[/yellow]")
        raise typer.Exit(1)

    console.print(f"[dim]Found subtitle ID {subtitle.id}[/dim]")

    with console.status(f"[bold green]Downloading subtitle {subtitle.id}..."):
        extracted = await download_and_extract_subtitle(filename, subtitle.id)

    # Use video file's stem with subtitle's extension
    subtitle_ext = Path(extracted.filename).suffix
    output_path = file.with_suffix(subtitle_ext)

    output_path.write_bytes(extracted.content)
    console.print(f"[green]Saved:[/green] {output_path}")
