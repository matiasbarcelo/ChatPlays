"""Keyboard input backend for macOS (vgamepad is Windows/Linux only)."""

import json
import logging
import platform
import subprocess
import time
from pathlib import Path

from pynput.keyboard import Controller, Key, KeyCode

IS_MAC = platform.system() == "Darwin"

# When set, keystrokes are targeted at this process by name instead of the
# frontmost app, so ChatPlays doesn't need focus and its own window is ignored.
_target_process: str = ""

_VBA_PROCESS_NAMES = ("visualboyadvance-m", "VisualBoyAdvance-M", "VisualBoyAdvance")


def set_target_process(name: str) -> None:
    global _target_process
    _target_process = name or ""


def _auto_detect_target() -> None:
    """Try to find a running VBA-M process and set it as the target."""
    global _target_process
    try:
        result = subprocess.run(
            ["pgrep", "-if", r"visualboyadvance|vbam"],
            capture_output=True, text=True, check=False, timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            set_target_process("visualboyadvance-m")
    except Exception:
        pass

# Defaults match common mGBA / OpenEmu-style bindings on macOS.
DEFAULT_KEYBOARD_MAPS = {
    "GBAController": {
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "a": "z",
        "b": "x",
        "l": "a",
        "r": "s",
        "select": "backspace",
        "start": "enter",
    },
    "XboxController": {
        "updpad": "up",
        "downdpad": "down",
        "leftdpad": "left",
        "rightdpad": "right",
        "a": "j",
        "b": "k",
        "x": "u",
        "y": "i",
        "back": "backspace",
        "start": "enter",
        "home": "h",
        "lb": "q",
        "rb": "e",
        "lt": "1",
        "rt": "2",
    },
    "PlayStationController": {
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "x": "j",
        "sq": "u",
        "cir": "k",
        "tri": "i",
        "select": "backspace",
        "start": "enter",
        "l1": "q",
        "r1": "e",
        "l2": "1",
        "r2": "2",
    },
}

SPECIAL_KEYS = {
    "enter": Key.enter,
    "return": Key.enter,
    "backspace": Key.backspace,
    "space": Key.space,
    "tab": Key.tab,
    "escape": Key.esc,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
}

ANALOG_INPUTS = {"lstick", "rstick", "left_joystick_float", "right_joystick_float",
                 "left_trigger_float", "right_trigger_float"}

CONFIG_PATH = Path(__file__).resolve().parent / "KeyboardMappings.json"

MAC_KEY_CODES = {
    Key.up: 126,
    Key.down: 125,
    Key.left: 123,
    Key.right: 124,
    Key.enter: 36,
    Key.backspace: 51,
    Key.space: 49,
    Key.tab: 48,
    Key.esc: 53,
}


def _resolve_key(key_name):
    if isinstance(key_name, (Key, KeyCode)):
        return key_name
    normalized = str(key_name).lower()
    if normalized in SPECIAL_KEYS:
        return SPECIAL_KEYS[normalized]
    if len(normalized) == 1:
        return KeyCode.from_char(normalized)
    return normalized


def _mac_press_key(key, duration: float) -> bool:
    """Send a key to the target process via System Events.

    Returns False (without sending) if no target process is configured, so
    keystrokes are never accidentally delivered to the ChatPlays window.
    """
    process = _target_process
    if not process:
        return False

    escaped_proc = process.replace("\\", "\\\\").replace('"', '\\"')

    if isinstance(key, Key):
        code = MAC_KEY_CODES.get(key)
        if code is None:
            return False
        repeats = max(1, round(duration / 0.08))
        script = f"""
tell application "System Events"
    tell process "{escaped_proc}"
        repeat {repeats} times
            key code {code}
            delay 0.08
        end repeat
    end tell
end tell
"""
    else:
        char = getattr(key, "char", None)
        if char is None and isinstance(key, str) and len(key) == 1:
            char = key
        if not char:
            return False
        escaped = char.replace("\\", "\\\\").replace('"', '\\"')
        script = f"""
tell application "System Events"
    tell process "{escaped_proc}"
        key down "{escaped}"
        delay {duration}
        key up "{escaped}"
    end tell
end tell
"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=max(int(duration) + 5, 5),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        logging.warning("osascript key press failed: %s", error)
        return False
    if result.returncode != 0:
        logging.warning("osascript key press error: %s", result.stderr.strip())
        return False
    return True


def load_keyboard_maps():
    """Load key maps from KeyboardMappings.json when present, else use defaults."""
    maps = {name: mapping.copy() for name, mapping in DEFAULT_KEYBOARD_MAPS.items()}
    if not CONFIG_PATH.is_file():
        return maps

    try:
        with CONFIG_PATH.open(encoding="utf-8") as config_file:
            overrides = json.load(config_file)
    except (json.JSONDecodeError, OSError) as error:
        logging.warning("Could not read KeyboardMappings.json: %s", error)
        return maps

    for controller_name, mapping in overrides.items():
        if controller_name in maps and isinstance(mapping, dict):
            maps[controller_name].update(mapping)
    return maps


def read_keyboard_mappings_file():
    """Return raw mapping file contents, or empty dict if missing."""
    if not CONFIG_PATH.is_file():
        return {}
    try:
        with CONFIG_PATH.open(encoding="utf-8") as config_file:
            data = json.load(config_file)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as error:
        logging.warning("Could not read KeyboardMappings.json: %s", error)
        return {}


def write_keyboard_mapping(controller_name, input_name, key_string):
    """Persist one input binding to KeyboardMappings.json."""
    data = read_keyboard_mappings_file()
    controller_map = data.get(controller_name)
    if not isinstance(controller_map, dict):
        controller_map = {}
    controller_map[input_name] = key_string
    data[controller_name] = controller_map
    _write_keyboard_mappings_file(data)


def write_keyboard_mappings(controller_name, mapping):
    """Persist multiple bindings for one controller."""
    data = read_keyboard_mappings_file()
    controller_map = data.get(controller_name)
    if not isinstance(controller_map, dict):
        controller_map = {}
    controller_map.update(mapping)
    data[controller_name] = controller_map
    _write_keyboard_mappings_file(data)


def _write_keyboard_mappings_file(data):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        json.dump(data, config_file, indent=4)
        config_file.write("\n")


def pynput_key_to_string(key):
    """Convert a captured pynput key to a KeyboardMappings.json value."""
    char = getattr(key, "char", None)
    if char is not None:
        return char.lower()
    name = getattr(key, "name", None)
    if name:
        return name.lower()
    return str(key).lower().replace("key.", "")


class KeyboardBackend:
    """Sends key press/release events through pynput (macOS Accessibility required)."""

    def __init__(self, controller_name, key_map):
        self.controller_name = controller_name
        self.key_map = {
            input_name: _resolve_key(key_name)
            for input_name, key_name in key_map.items()
        }
        self._keyboard = Controller()
        self._warned_about_permissions = False

    def press_input(self, input_name, duration):
        if input_name in ANALOG_INPUTS:
            logging.warning(
                "Keyboard backend cannot simulate analog input %r on macOS; bind a key in KeyboardMappings.json or use Windows/Linux with vgamepad.",
                input_name,
            )
            return

        mapped = self.key_map.get(input_name)
        if mapped is None:
            logging.warning("No keyboard mapping for input %r (%s)", input_name, self.controller_name)
            return

        logging.info(
            "Keyboard press: controller=%s input=%r -> key=%r duration=%s",
            self.controller_name,
            input_name,
            getattr(mapped, "char", mapped),
            duration,
        )
        if IS_MAC:
            # On macOS always use AppleScript targeted at the emulator process so
            # keystrokes never land in the ChatPlays window regardless of focus.
            # If _target_process isn't set yet, try to auto-detect VBA-M.
            if not _target_process:
                _auto_detect_target()
            if not _mac_press_key(mapped, duration):
                logging.warning(
                    "Keyboard press failed for %r — is the emulator running and does "
                    "Python have Accessibility permission?",
                    input_name,
                )
            return

        try:
            self._keyboard.press(mapped)
            time.sleep(duration)
            self._keyboard.release(mapped)
        except Exception as error:
            if not self._warned_about_permissions:
                logging.error(
                    "Keyboard input failed (%s). On macOS, grant Accessibility permission to Terminal, Python, or Electron under System Settings > Privacy & Security > Accessibility.",
                    error,
                )
                self._warned_about_permissions = True
            raise
