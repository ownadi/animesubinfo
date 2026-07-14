"""Kodi entry point for the AnimeSub.info subtitle service."""

import os
import sys

# Releases place packages in resources/lib. The src fallback makes a checkout
# directly runnable while developing the add-on.
root = os.path.dirname(__file__)
for library_dir in ("resources/lib", "src"):
    path = os.path.join(root, library_dir)
    if path not in sys.path:
        sys.path.insert(0, path)

from animesubinfo_kodi.addon import run


if __name__ == "__main__":
    run()
