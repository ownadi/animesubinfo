"""Adapter between Kodi's subtitle protocol and the core library."""

import asyncio
import os
import sys
import traceback
from typing import Any
from urllib.parse import parse_qs, unquote, urlencode

from animesubinfo import (
    ExtractedSubtitle,
    SubtitleMatch,
    Subtitles,
    download_and_extract_subtitle,
    find_subtitle_matches,
)

from .service import SubtitleService

_METADATA_VALUE_LIMIT = 16


async def _find(video_name: str) -> list[SubtitleMatch]:
    return await find_subtitle_matches(video_name)


async def _download(video_name: str, subtitle_id: int) -> ExtractedSubtitle:
    return await download_and_extract_subtitle(video_name, subtitle_id)


def _query(raw_query: str) -> dict[str, str]:
    """Parse Kodi's plug-in query string into single-value parameters."""
    return {
        key: values[0]
        for key, values in parse_qs(raw_query.lstrip("?")).items()
        if values
    }


def _video_name(xbmc: Any, params: dict[str, str]) -> str:
    """Build the filename-like value used by the core matching algorithm."""
    manual = unquote(params.get("searchstring", "")).strip()
    episode = xbmc.getInfoLabel("VideoPlayer.Episode").strip()
    if manual:
        return f"{manual} - {episode}" if episode else manual

    playing = unquote(xbmc.Player().getPlayingFile())
    name = os.path.basename(playing.rstrip("/"))
    if name:
        return name

    title = xbmc.getInfoLabel("VideoPlayer.OriginalTitle").strip()
    title = title or xbmc.getInfoLabel("VideoPlayer.TVShowTitle").strip()
    title = title or xbmc.getInfoLabel("VideoPlayer.Title").strip()
    return f"{title} - {episode}" if title and episode else title


def _rating(subtitle: Subtitles) -> str:
    """Convert AnimeSub.info votes to Kodi's zero-to-five icon rating."""
    votes = subtitle.rating
    total = votes.bad + votes.average + votes.very_good
    if not total:
        return "0"
    weighted = votes.average * 3 + votes.very_good * 5
    return str(round(weighted / total))


def _result_details(subtitle: Subtitles) -> str:
    """Build the metadata shown in Kodi's secondary subtitle label."""
    def compact(value: str) -> str:
        value = " ".join(value.split()) or "Unknown"
        if len(value) <= _METADATA_VALUE_LIMIT:
            return value
        return f"{value[: _METADATA_VALUE_LIMIT - 1]}…"

    return (
        f"{subtitle.date.isoformat()} · "
        f"A: {compact(subtitle.author)} · U: {compact(subtitle.added_by)}"
    )


def run(argv: list[str] | None = None) -> None:
    """Handle one invocation from Kodi."""
    import xbmc
    import xbmcaddon
    import xbmcgui
    import xbmcplugin
    import xbmcvfs

    args = argv or sys.argv
    handle = int(args[1])
    params = _query(args[2] if len(args) > 2 else "")
    action = params.get("action", "search")
    video_name = _video_name(xbmc, params)
    service = SubtitleService(_find, _download)

    try:
        if action in {"search", "manualsearch"}:
            matches = asyncio.run(service.search(video_name))
            for match in matches:
                subtitle = match.subtitle
                item = xbmcgui.ListItem(
                    label="Polish", label2=_result_details(subtitle)
                )
                item.setArt({"icon": _rating(subtitle)})
                item.setProperty(
                    "sync",
                    "true" if match.is_probably_synced else "false",
                )
                item.setProperty("hearing_imp", "false")
                download_params = {
                    "action": "download",
                    "id": subtitle.id,
                    "video": video_name,
                }
                url = f"{args[0]}?{urlencode(download_params)}"
                xbmcplugin.addDirectoryItem(handle, url, item, isFolder=False)
        elif action == "download":
            profile = xbmcaddon.Addon().getAddonInfo("profile")
            destination = xbmcvfs.translatePath(profile)
            requested_video = params.get("video", video_name)
            path = asyncio.run(
                service.download(requested_video, int(params["id"]), destination)
            )
            item = xbmcgui.ListItem(label=path)
            xbmcplugin.addDirectoryItem(handle, path, item, isFolder=False)
    except Exception as error:
        xbmc.log(
            f"AnimeSub.info subtitle error: {error}\n{traceback.format_exc()}",
            xbmc.LOGERROR,
        )
        xbmcgui.Dialog().notification(
            "AnimeSub.info", "Could not retrieve subtitles", xbmcgui.NOTIFICATION_ERROR
        )
    finally:
        xbmcplugin.endOfDirectory(handle)
