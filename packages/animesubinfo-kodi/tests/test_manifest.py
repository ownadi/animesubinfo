"""Tests for the installable Kodi add-on manifest."""

import tomllib
from pathlib import Path
from xml.etree import ElementTree


PACKAGE_ROOT = Path(__file__).parents[1]


def test_manifest_declares_subtitle_entry_point() -> None:
    root = ElementTree.parse(PACKAGE_ROOT / "addon.xml").getroot()

    assert root.attrib["id"] == "service.subtitles.animesubinfo"
    extension = root.find("./extension[@point='xbmc.subtitle.module']")
    assert extension is not None
    assert extension.attrib["library"] == "default.py"


def test_manifest_and_python_package_versions_match() -> None:
    root = ElementTree.parse(PACKAGE_ROOT / "addon.xml").getroot()
    with (PACKAGE_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    assert root.attrib["version"] == "0.1.0"
    assert root.attrib["version"] == pyproject["project"]["version"]
    assert "animesubinfo>=0.4.0" in pyproject["project"]["dependencies"]
