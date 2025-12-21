"""Download command for fetching subtitle files."""

import asyncio
from pathlib import Path
from typing import Annotated, Optional

import typer

from animesubinfo import download_subtitles

from ..output import console

app = typer.Typer()


@app.command()
def download(
    subtitle_id: Annotated[int, typer.Argument(help="Subtitle ID to download")],
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output",
            "-o",
            help="Output file path (defaults to original filename)",
        ),
    ] = None,
) -> None:
    """Download a subtitle file by its ID."""
    asyncio.run(_download_async(subtitle_id, output))


async def _download_async(subtitle_id: int, output: Optional[Path]) -> None:
    """Async implementation of download command."""
    with console.status(f"[bold green]Downloading subtitle {subtitle_id}..."):
        async with download_subtitles(subtitle_id) as result:
            output_path = output or Path(result.filename)

            content = bytearray()
            async for chunk in result.content:
                content.extend(chunk)

            output_path.write_bytes(content)

    console.print(f"[green]Downloaded:[/green] {output_path}")
