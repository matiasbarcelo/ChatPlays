"""Where ChatPlays reads and writes its files, from source or as an installed build."""

import os
import platform
import sys
from pathlib import Path

IS_FROZEN = getattr(sys, "frozen", False)
SOURCE_DIR = Path(__file__).resolve().parent


def user_data_dir() -> Path:
    override = os.environ.get("CHATPLAYS_USER_DATA", "").strip()
    if override:
        return Path(override)

    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        return base / "ChatPlays"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "ChatPlays"
    return Path.home() / ".config" / "chatplays"


def config_file(name: str) -> Path:
    # An installed build can't keep user edits in its install folder: updates replace it.
    return user_data_dir() / name if IS_FROZEN else SOURCE_DIR / name
