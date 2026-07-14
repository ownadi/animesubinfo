# animesubinfo

Python client and tools for searching and downloading anime subtitles from [AnimeSub.info](http://animesub.info).

## Packages

- **[animesubinfo](./packages/animesubinfo)** - Core library
- **[animesubinfo-cli](./packages/animesubinfo-cli)** - Command-line interface
- **[animesubinfo-kodi](./packages/animesubinfo-kodi)** - Kodi subtitle service add-on

## Development

### Setup

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync all workspace packages
uv sync --all-packages
```

### Running tests

```bash
# Run tests for all packages
uv run --package animesubinfo pytest
uv run --package animesubinfo-cli pytest
uv run --package animesubinfo-kodi pytest
```

### Publishing

The core library and CLI are published independently with version-specific
tags:

```bash
# Tag for library release
git tag animesubinfo-v0.1.0

# Tag for CLI release
git tag animesubinfo-cli-v0.1.0
```

For a Kodi release, create and push its version tag, then publish a GitHub
Release for that same tag:

```bash
git tag animesubinfo-kodi-v0.1.0
git push origin animesubinfo-kodi-v0.1.0
```

Publishing the release builds the add-on with Python 3.11 and attaches the
installable ZIP directly to the release.
