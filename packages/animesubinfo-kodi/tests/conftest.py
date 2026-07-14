"""Shared fixtures for the Kodi add-on tests."""

import sys
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from animesubinfo import Subtitles, SubtitlesRating


def make_subtitle(
    subtitle_id: int = 12345,
    *,
    author: str = "Subtitle Author",
    uploader: str = "Upload User",
    uploaded: date = date(2024, 1, 15),
) -> Subtitles:
    return Subtitles(
        id=subtitle_id,
        episode=1,
        to_episode=1,
        original_title="Test Anime",
        english_title="Test Anime English",
        alt_title="",
        date=uploaded,
        format="ass",
        author=author,
        added_by=uploader,
        size="15 KB",
        description="Test description",
        comment_count=0,
        downloaded_times=10,
        rating=SubtitlesRating(bad=0, average=20, very_good=80),
    )


@pytest.fixture
def sample_subtitle() -> Subtitles:
    return make_subtitle()


class FakeListItem:
    def __init__(self, label: str = "", label2: str = "", **kwargs) -> None:
        self.label = label
        self.label2 = label2
        self.art: dict[str, str] = {}
        self.properties: dict[str, str] = {}

    def setArt(self, art: dict[str, str]) -> None:
        self.art.update(art)

    def setProperty(self, key: str, value: str) -> None:
        self.properties[key] = value


@pytest.fixture
def kodi_modules(monkeypatch: pytest.MonkeyPatch, tmp_path):
    state = SimpleNamespace(
        playing_file="/videos/Test Anime - 01.mkv",
        labels={"VideoPlayer.Episode": "1"},
        directory_items=[],
        logs=[],
        notifications=[],
        profile=str(tmp_path / "profile"),
    )

    class Player:
        def getPlayingFile(self) -> str:
            return state.playing_file

    xbmc = SimpleNamespace(
        Player=Player,
        getInfoLabel=lambda key: state.labels.get(key, ""),
        log=lambda message, level: state.logs.append((message, level)),
        LOGERROR=4,
    )

    class Addon:
        def getAddonInfo(self, key: str) -> str:
            assert key == "profile"
            return state.profile

    xbmcaddon = SimpleNamespace(Addon=Addon)

    class Dialog:
        def notification(self, *args) -> None:
            state.notifications.append(args)

    xbmcgui = SimpleNamespace(
        ListItem=FakeListItem,
        Dialog=Dialog,
        NOTIFICATION_ERROR="error",
    )
    xbmcplugin = SimpleNamespace(
        addDirectoryItem=lambda *args, **kwargs: state.directory_items.append(
            (args, kwargs)
        ),
        endOfDirectory=Mock(),
    )
    xbmcvfs = SimpleNamespace(translatePath=lambda path: path)

    for name, module in {
        "xbmc": xbmc,
        "xbmcaddon": xbmcaddon,
        "xbmcgui": xbmcgui,
        "xbmcplugin": xbmcplugin,
        "xbmcvfs": xbmcvfs,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    state.xbmcplugin = xbmcplugin
    return state
