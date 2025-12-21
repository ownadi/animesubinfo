# animesubinfo-cli

Command-line interface for searching and downloading anime subtitles from AnimeSub.info.

## Installation

Install globally as a CLI tool:

```bash
uv tool install animesubinfo-cli
```

Or with pipx:

```bash
pipx install animesubinfo-cli
```

After installation, the `animesubinfo` command will be available system-wide.

## Commands

### search

Search for subtitles by anime title:

```bash
animesubinfo search "Attack on Titan"
```

Options:
- `--sort`, `-s` - Sort results (traf, t_org, t_en, t_pl, pobrn, datad)
- `--type`, `-t` - Filter by title type (org, en, pl)
- `--limit`, `-l` - Maximum number of pages to fetch
- `--json`, `-j` - Output results as JSON

### find

Find the best matching subtitle for a video file (displays info only):

```bash
animesubinfo find "[SubGroup] Attack on Titan - 12 [1080p].mkv"
```

Options:
- `--json`, `-j` - Output result as JSON

### download

Download a subtitle archive by its ID:

```bash
animesubinfo download 12345
animesubinfo download 12345 -o subtitles.zip
```

Options:
- `--output`, `-o` - Output file path (defaults to original filename)

### best

Find and download the best matching subtitle for a video file:

```bash
animesubinfo best "[SubGroup] Attack on Titan - 12 [1080p].mkv"
```

This command:
1. Finds the best matching subtitle for the video file
2. Downloads and extracts the subtitle
3. Saves it with the same name as the video file (e.g., `video.mkv` → `video.ass`)

## Examples

Search for subtitles sorted by downloads:
```bash
animesubinfo search "Naruto" --sort pobrn
```

Get JSON output for scripting:
```bash
animesubinfo search "One Piece" --json | jq '.[0].id'
```

Download subtitle for a specific episode:
```bash
animesubinfo best "[Erai-raws] Jujutsu Kaisen - 01 [1080p].mkv"
```
