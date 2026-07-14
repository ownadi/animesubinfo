"""Tests for Kodi bundle validation."""

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "build_addon.py"
SPEC = importlib.util.spec_from_file_location("build_addon", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
build_addon = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_addon)


def test_validate_libraries_accepts_copied_packages(tmp_path: Path) -> None:
    for package in ("animesubinfo", "animesubinfo_kodi"):
        package_directory = tmp_path / package
        package_directory.mkdir()
        (package_directory / "__init__.py").touch()
    (tmp_path / "typing_extensions.py").touch()

    build_addon._validate_libraries(tmp_path)


def test_validate_libraries_rejects_editable_core_reference(tmp_path: Path) -> None:
    for package in ("animesubinfo", "animesubinfo_kodi"):
        package_directory = tmp_path / package
        package_directory.mkdir()
        (package_directory / "__init__.py").touch()
    (tmp_path / "typing_extensions.py").touch()
    (tmp_path / "animesubinfo.pth").write_text("/local/source", encoding="utf-8")

    with pytest.raises(RuntimeError, match="editable animesubinfo.pth"):
        build_addon._validate_libraries(tmp_path)
