# animesubinfo

Python client and tools for searching and downloading anime subtitles from [AnimeSub.info](http://animesub.info).

## Packages

- **[animesubinfo](./packages/animesubinfo)** - Core library
- **[animesubinfo-cli](./packages/animesubinfo-cli)** - Command-line interface (in development)

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
```

### Publishing

Packages are published independently with version-specific tags:

```bash
# Tag for library release
git tag animesubinfo-v0.1.0

# Tag for CLI release
git tag animesubinfo-cli-v0.1.0
```
