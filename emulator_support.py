"""Detect emulators and read their controller bindings for automatic setup."""

from __future__ import annotations

import logging
import platform
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

IS_MAC = platform.system() == "Darwin"

VBA_JOY0_TO_INPUT = {
    "Joy0_Up": "up",
    "Joy0_Down": "down",
    "Joy0_Left": "left",
    "Joy0_Right": "right",
    "Joy0_A": "a",
    "Joy0_B": "b",
    "Joy0_L": "l",
    "Joy0_R": "r",
    "Joy0_Start": "start",
    "Joy0_Select": "select",
}

# VisualBoyAdvance default keyboard bindings (SDL keysyms, hex).
VBA_DEFAULT_KEYBOARD = {
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "a": "z",
    "b": "x",
    "l": "a",
    "r": "s",
    "start": "enter",
    "select": "backspace",
}

SDL_KEYSYMS: Dict[int, str] = {
    0x008: "backspace",
    0x009: "tab",
    0x00D: "enter",
    0x01B: "escape",
    0x020: "space",
    0x111: "up",
    0x112: "down",
    0x113: "right",
    0x114: "left",
    0x104: "kp_4",
    0x106: "kp_6",
    0x108: "kp_8",
    0x102: "kp_2",
}

VBA_PROCESS_NAMES = (
    "VisualBoyAdvance-M",
    "visualboyadvance-m",
    "VisualBoyAdvance",
    "VisualBoyAdvance.app",
)

VBA_CONFIG_CANDIDATES = (
    Path.home() / "Library/Application Support/visualboyadvance-m/vbam.ini",
    Path.home() / "Library/Application Support/VBA-M/vbam.ini",
    Path.home() / "Library/Application Support/VisualBoyAdvance-M/vbam.ini",
    Path.home() / "Library/Preferences/vbam.ini",
    Path.home() / ".config/vbam/vbam.ini",
    Path.home() / ".vbam/vbam.ini",
)


@dataclass
class EmulatorDetection:
    found: bool
    emulator_id: str = ""
    display_name: str = ""
    app_name: str = ""
    window_title: str = ""
    config_path: str = ""
    message: str = ""


def _run_osascript(script: str) -> tuple[str, str]:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode != 0:
            return "", result.stderr.strip()
        return result.stdout.strip(), ""
    except (OSError, subprocess.TimeoutExpired) as error:
        logger.debug("osascript failed: %s", error)
        return "", str(error)


def _find_vba_process_via_pgrep() -> Optional[str]:
    try:
        result = subprocess.run(
            ["pgrep", "-if", r"visualboyadvance|vbam\.app|vbam\b"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    first_line = result.stdout.strip().splitlines()[0]
    parts = first_line.split(None, 1)
    return parts[1] if len(parts) > 1 else parts[0]


def _find_vbam_config() -> Optional[Path]:
    for candidate in VBA_CONFIG_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def _detect_vba_on_mac() -> EmulatorDetection:
    script = """
set output to ""
tell application "System Events"
    repeat with proc in (every application process whose background only is false)
        set procName to name of proc
        if procName contains "visualboyadvance" or procName contains "VisualBoyAdvance" or procName contains "vbam" or procName contains "VBA" then
            set windowTitle to ""
            try
                if (count of windows of proc) > 0 then
                    set windowTitle to name of front window of proc
                end if
            end try
            set output to procName & "|||" & windowTitle
            exit repeat
        end if
    end repeat
end tell
return output
"""
    raw, osascript_error = _run_osascript(script)
    config_path = _find_vbam_config()
    pgrep_name = _find_vba_process_via_pgrep()

    if not raw and pgrep_name:
        app_name = pgrep_name
        window_title = pgrep_name
        config_note = f" Config: {config_path.name}" if config_path else " Using VBA default keys."
        note = ""
        if osascript_error:
            note = " (Grant Terminal/Python Accessibility access in System Settings for window focus.)"
        return EmulatorDetection(
            found=True,
            emulator_id="visualboyadvance",
            display_name="VisualBoy Advance",
            app_name=app_name,
            window_title=window_title,
            config_path=str(config_path) if config_path else "",
            message=f"Found running process “{app_name}”.{config_note}{note}",
        )

    if not raw:
        if pgrep_name or config_path:
            message = "VisualBoy Advance is not running. Open the emulator, then scan again."
            if osascript_error and "Not authorized" in osascript_error:
                message = (
                    "Could not inspect running apps. Grant Accessibility access to "
                    "Terminal or Python in System Settings → Privacy & Security → Accessibility."
                )
            return EmulatorDetection(
                found=False,
                emulator_id="visualboyadvance",
                display_name="VisualBoy Advance",
                config_path=str(config_path) if config_path else "",
                message=message,
            )
        return EmulatorDetection(
            found=False,
            emulator_id="visualboyadvance",
            display_name="VisualBoy Advance",
            message="VisualBoy Advance not found. Launch VBA-M, then click Scan for Emulator.",
        )

    parts = raw.split("|||", 1)
    app_name = parts[0].strip()
    window_title = parts[1].strip() if len(parts) > 1 else ""

    if not window_title:
        window_title = app_name

    config_note = f" Config: {config_path.name}" if config_path else " Using VBA default keys."

    return EmulatorDetection(
        found=True,
        emulator_id="visualboyadvance",
        display_name="VisualBoy Advance",
        app_name=app_name,
        window_title=window_title,
        config_path=str(config_path) if config_path else "",
        message=f"Targeting window “{window_title}”.{config_note}",
    )


def scan_for_emulator(controller_label: str = "GBA") -> EmulatorDetection:
    if controller_label != "GBA":
        return EmulatorDetection(
            found=False,
            message="Automatic setup currently supports GBA with VisualBoy Advance only.",
        )

    if IS_MAC:
        return _detect_vba_on_mac()

    return EmulatorDetection(
        found=False,
        emulator_id="visualboyadvance",
        display_name="VisualBoy Advance",
        message="Automatic emulator detection is not implemented on this platform yet.",
    )


def focus_emulator(detection: EmulatorDetection) -> bool:
    if not detection.found or not detection.app_name:
        return False
    if not IS_MAC:
        return False
    app_name = detection.app_name.replace('"', '\\"')
    _, error = _run_osascript(f'tell application "{app_name}" to activate')
    if not error:
        return True
    try:
        result = subprocess.run(
            ["open", "-a", detection.app_name],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _parse_ini_bindings(config_path: Path) -> Dict[str, str]:
    bindings: Dict[str, str] = {}
    for line in config_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            key, value = stripped.split("=", 1)
        else:
            match = re.match(r"^(\S+)\s+(\S+)$", stripped)
            if not match:
                continue
            key, value = match.group(1), match.group(2)
        bindings[key.strip()] = value.strip()
    return bindings


def _is_keyboard_binding(value: str) -> bool:
    cleaned = value.strip().lower()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    if not cleaned:
        return False
    if not re.fullmatch(r"[0-9a-f]+", cleaned):
        return False
    return cleaned[0] == "0"


def _sdl_to_key_name(code: int) -> Optional[str]:
    if code in SDL_KEYSYMS:
        return SDL_KEYSYMS[code]
    if 0x61 <= code <= 0x7A:
        return chr(code)
    if 0x41 <= code <= 0x5A:
        return chr(code).lower()
    if 0x30 <= code <= 0x39:
        return chr(code)
    return None


def _binding_value_to_key(value: str) -> Optional[str]:
    if not _is_keyboard_binding(value):
        return None
    code = int(value.strip().lower().removeprefix("0x"), 16)
    return _sdl_to_key_name(code)


def read_vba_gba_keyboard_map(config_path: Optional[str] = None) -> tuple[Dict[str, str], str]:
    """Return ChatPlays GBA input names mapped to keyboard key strings."""
    mapping = dict(VBA_DEFAULT_KEYBOARD)
    source = "VBA defaults"

    path = Path(config_path) if config_path else _find_vbam_config()
    if path and path.is_file():
        bindings = _parse_ini_bindings(path)
        parsed_any = False
        for joy_key, input_name in VBA_JOY0_TO_INPUT.items():
            raw_value = bindings.get(joy_key)
            if not raw_value:
                continue
            key_name = _binding_value_to_key(raw_value)
            if key_name:
                mapping[input_name] = key_name
                parsed_any = True
        if parsed_any:
            source = path.name

    return mapping, source


def build_auto_link_summary(mapping: Dict[str, str], source: str) -> str:
    pairs = ", ".join(f"{name}={key}" for name, key in sorted(mapping.items()))
    return f"Linked using {source}: {pairs}"
