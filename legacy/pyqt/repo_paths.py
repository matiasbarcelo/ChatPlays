"""Paths back to the repo root (legacy PyQt UI lives under legacy/pyqt/)."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = REPO_ROOT / "UI" / "assets"
FONTS_DIR = REPO_ROOT / "UI" / "fonts"


def ensure_repo_on_path():
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def asset(filename: str) -> str:
    return str(ASSETS_DIR / filename)
