"""Build a self-contained, installable Kodi add-on ZIP."""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile

ADDON_ID = "service.subtitles.animesubinfo"
KODI_PYTHON_VERSION = "3.11"


def _run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def _find_wheel(wheel_directory: Path, distribution: str) -> Path:
    matches = sorted(wheel_directory.glob(f"{distribution}-*.whl"))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one wheel for {distribution}, found {len(matches)}"
        )
    return matches[0]


def _validate_libraries(library_directory: Path) -> None:
    required_files = (
        library_directory / "animesubinfo" / "__init__.py",
        library_directory / "animesubinfo_kodi" / "__init__.py",
        library_directory / "typing_extensions.py",
    )
    missing = [path for path in required_files if not path.is_file()]
    if missing:
        names = ", ".join(str(path.relative_to(library_directory)) for path in missing)
        raise RuntimeError(f"Kodi bundle is missing required packages: {names}")

    editable_reference = library_directory / "animesubinfo.pth"
    if editable_reference.exists():
        raise RuntimeError("Kodi bundle contains an editable animesubinfo.pth")


def build_addon(output: Path | None = None) -> Path:
    script_path = Path(__file__).resolve()
    package_root = script_path.parents[1]
    repository_root = script_path.parents[3]
    core_root = repository_root / "packages" / "animesubinfo"

    manifest = ElementTree.parse(package_root / "addon.xml").getroot()
    version = manifest.attrib["version"]
    archive_path = output or (
        repository_root / "dist" / f"{ADDON_ID}-{version}.zip"
    )
    archive_path = archive_path.resolve()
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="animesubinfo-kodi-") as temporary:
        staging_root = Path(temporary)
        addon_root = staging_root / ADDON_ID
        library_directory = addon_root / "resources" / "lib"
        wheel_directory = staging_root / "wheels"
        library_directory.mkdir(parents=True)
        wheel_directory.mkdir()

        shutil.copy2(package_root / "addon.xml", addon_root / "addon.xml")
        shutil.copy2(package_root / "default.py", addon_root / "default.py")

        for package_name in ("animesubinfo", "animesubinfo-kodi"):
            _run(
                [
                    "uv",
                    "build",
                    "--wheel",
                    "--package",
                    package_name,
                    "--out-dir",
                    str(wheel_directory),
                ],
                cwd=repository_root,
            )

        core_wheel = _find_wheel(wheel_directory, "animesubinfo")
        kodi_wheel = _find_wheel(wheel_directory, "animesubinfo_kodi")
        _run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                sys.executable,
                "--target",
                str(library_directory),
                "--python-version",
                KODI_PYTHON_VERSION,
                "--no-compile",
                "--no-sources",
                str(core_wheel),
                str(kodi_wheel),
            ],
            cwd=repository_root,
        )

        _validate_libraries(library_directory)

        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(addon_root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(staging_root).as_posix())

    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Output ZIP path (defaults to dist/<addon-id>-<version>.zip)",
    )
    args = parser.parse_args()
    print(build_addon(args.output))


if __name__ == "__main__":
    main()
