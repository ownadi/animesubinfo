"""Tests for Kodi subtitle protocol integration."""

from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from animesubinfo import ExtractedSubtitle, SubtitleMatch
from animesubinfo_kodi import addon

from conftest import make_subtitle


def test_result_details_include_author_uploader_and_upload_date(
    sample_subtitle,
) -> None:
    details = addon._result_details(sample_subtitle)

    assert details == "2024-01-15 · A: Subtitle Author · U: Upload User"


def test_result_details_bound_long_metadata(sample_subtitle) -> None:
    sample_subtitle.author = "An exceptionally long subtitle author"
    sample_subtitle.added_by = "An exceptionally long uploader name"

    details = addon._result_details(sample_subtitle)

    assert details == "2024-01-15 · A: An exceptionall… · U: An exceptionall…"
    assert len(details) == 54


def test_search_lists_every_match_in_core_ranking_order(
    monkeypatch, kodi_modules
) -> None:
    subtitles = [
        make_subtitle(20, uploaded=date(2025, 2, 1)),
        make_subtitle(10, uploaded=date(2024, 1, 1)),
    ]
    ranked = [
        SubtitleMatch(subtitle=subtitles[0], score=(101 << 8) | (1 << 5)),
        SubtitleMatch(subtitle=subtitles[1], score=101 << 8),
    ]

    def calculate_fitness(*args):
        raise AssertionError("Kodi must use the fitness calculated by core")

    monkeypatch.setattr(type(subtitles[0]), "calculate_fitness", calculate_fitness)
    searched: list[str] = []

    async def find(video_name: str):
        searched.append(video_name)
        return ranked

    monkeypatch.setattr(addon, "_find", find)

    addon.run(["plugin://service.subtitles.animesubinfo", "7", "?action=search"])

    assert searched == ["Test Anime - 01.mkv"]
    assert len(kodi_modules.directory_items) == 2

    listed_ids: list[int] = []
    for index, ((args, kwargs), match) in enumerate(
        zip(kodi_modules.directory_items, ranked)
    ):
        subtitle = match.subtitle
        handle, url, item = args
        assert handle == 7
        assert kwargs == {"isFolder": False}
        assert item.label == "Polish"
        assert item.label2 == (
            f"{subtitle.date.isoformat()} · A: Subtitle Author · U: Upload User"
        )
        assert item.properties == {
            "sync": "true" if index == 0 else "false",
            "hearing_imp": "false",
        }
        listed_ids.append(int(parse_qs(urlparse(url).query)["id"][0]))

    assert listed_ids == [20, 10]
    kodi_modules.xbmcplugin.endOfDirectory.assert_called_once_with(7)


def test_manual_search_combines_title_with_current_episode(
    monkeypatch, kodi_modules
) -> None:
    searched: list[str] = []

    async def find(video_name: str):
        searched.append(video_name)
        return []

    monkeypatch.setattr(addon, "_find", find)

    addon.run(
        [
            "plugin://service.subtitles.animesubinfo",
            "9",
            "?action=manualsearch&searchstring=Frieren",
        ]
    )

    assert searched == ["Frieren - 1"]


def test_download_returns_saved_subtitle_path(
    monkeypatch, kodi_modules
) -> None:
    downloaded: list[tuple[str, int]] = []

    async def download(video_name: str, subtitle_id: int):
        downloaded.append((video_name, subtitle_id))
        return ExtractedSubtitle("../Test Anime - 01.ass", b"subtitle")

    monkeypatch.setattr(addon, "_download", download)

    addon.run(
        [
            "plugin://service.subtitles.animesubinfo",
            "11",
            "?action=download&id=42&video=Test+Anime+-+01.mkv",
        ]
    )

    assert downloaded == [("Test Anime - 01.mkv", 42)]
    args, kwargs = kodi_modules.directory_items[0]
    expected_path = Path(kodi_modules.profile) / "Test Anime - 01.ass"
    assert args[0] == 11
    assert args[1] == str(expected_path)
    assert args[2].label == str(expected_path)
    assert kwargs == {"isFolder": False}
    assert expected_path.read_bytes() == b"subtitle"
