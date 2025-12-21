"""Main CLI entry point for animesubinfo."""

import typer

from .commands import best_app, download_app, find_app, search_app

app = typer.Typer(
    name="animesubinfo",
    help="Search and find anime subtitles from AnimeSub.info",
    no_args_is_help=True,
)

app.add_typer(search_app)
app.add_typer(find_app)
app.add_typer(download_app)
app.add_typer(best_app)


def main() -> int:
    """Entry point for the CLI."""
    app()

    return 0
