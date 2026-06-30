"""Persist main-window settings (e.g. last Twitch username) across sessions."""

import json
import logging
import os
import platform
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_KEYS = (
    "twitch_username",
    "twitch_username_verified",
    "twitch_display_name",
    "streaming_platform",
)


def _user_settings_dir() -> Path:
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


def _settings_file() -> Path:
    return _user_settings_dir() / "main_settings.json"


def load_main_settings_cache() -> dict[str, Any]:
    path = _settings_file()
    if not path.is_file():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read cached main settings from %s: %s", path, exc)
        return {}

    if not isinstance(data, dict):
        return {}

    return {key: data[key] for key in _CACHE_KEYS if key in data}


def save_main_settings_cache(settings: dict[str, Any]) -> None:
    path = _settings_file()
    payload = {key: settings.get(key) for key in _CACHE_KEYS if key in settings}

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not write cached main settings to %s: %s", path, exc)
