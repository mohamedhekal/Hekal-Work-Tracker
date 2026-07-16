"""Resolve writable data directories for dev and bundled app runs."""

from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "HekalWorkTracker"


def get_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / APP_NAME
        elif sys.platform == "win32":
            base = Path.home() / "AppData" / "Roaming" / APP_NAME
        else:
            base = Path.home() / ".local" / "share" / APP_NAME
        return base / "data"

    return Path(__file__).resolve().parent / "data"
