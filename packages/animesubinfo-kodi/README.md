# animesubinfo-kodi

Kodi subtitle service for Polish anime subtitles from
[AnimeSub.info](http://animesub.info). The add-on uses the `animesubinfo` core
package to find every compatible subtitle for the current episode, rank the
matches by fitness, and extract the best file from the selected download.

Each Kodi search result shows the subtitle author, uploader, and upload date.

## Add-on layout

Kodi expects an installable ZIP with a top-level directory named
`service.subtitles.animesubinfo`. That directory must contain `addon.xml` and
`default.py`; this package and the core library with its runtime dependencies
belong under `resources/lib`.

During development, `default.py` also loads this package directly from `src`.

Build a self-contained ZIP from the workspace root with:

```bash
uv run --python 3.11 python packages/animesubinfo-kodi/scripts/build_addon.py
```

The builder installs wheels rather than editable workspace packages and
resolves conditional dependencies for Kodi 21's Python 3.11 runtime. This is
important because editable installs contain local `.pth` references that Kodi
cannot resolve, while resolving against a newer host Python can omit Kodi's
compatibility dependencies.

## Development

```bash
uv run --package animesubinfo-kodi pytest
```
