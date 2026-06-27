"""Detect emulators and read their controller bindings for automatic setup."""

from __future__ import annotations

import logging
import platform
import re
import subprocess
import time
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

# VBA-M IniVersion=1 joypad section ([Joypad/1]).
VBA_JOY1_FIELD_TO_INPUT = {
    "Up": "up",
    "Down": "down",
    "Left": "left",
    "Right": "right",
    "A": "a",
    "B": "b",
    "L": "l",
    "R": "r",
    "Select": "select",
    "Start": "start",
}

VBA_JOY1_CORE_FIELDS = tuple(VBA_JOY1_FIELD_TO_INPUT.keys())

CHATPLAYS_KEY_TO_VBA_STRING = {
    "up": "UP",
    "down": "DOWN",
    "left": "LEFT",
    "right": "RIGHT",
    "z": "Z",
    "x": "X",
    "a": "A",
    "s": "S",
    "c": "C",
    "v": "V",
    "backspace": "BACK",
    "enter": "ENTER",
    "return": "ENTER",
    "space": "SPACE",
    "tab": "TAB",
    "escape": "ESC",
}

VBA_STRING_TO_CHATPLAYS_KEY = {
    "UP": "up",
    "DOWN": "down",
    "LEFT": "left",
    "RIGHT": "right",
    "BACK": "backspace",
    "BACKSPACE": "backspace",
    "ENTER": "enter",
    "RETURN": "enter",
    "SPACE": "space",
    "TAB": "tab",
    "ESC": "escape",
    "ESCAPE": "escape",
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


OSASCRIPT_DEFAULT_TIMEOUT = 8
OSASCRIPT_UI_TIMEOUT = 15


def _run_osascript(script: str, *, timeout: float = OSASCRIPT_DEFAULT_TIMEOUT) -> tuple[str, str]:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
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


def _all_vbam_configs() -> list[Path]:
    seen: set[Path] = set()
    configs: list[Path] = []
    for candidate in VBA_CONFIG_CANDIDATES:
        resolved = candidate.resolve()
        if candidate.is_file() and resolved not in seen:
            seen.add(resolved)
            configs.append(candidate)
    return configs


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
    raw, osascript_error = _run_osascript(script, timeout=OSASCRIPT_UI_TIMEOUT)
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


def scan_for_emulator(
    controller_label: str = "GBA",
    emulator_id: str = "visualboyadvance",
) -> EmulatorDetection:
    if controller_label != "GBA":
        return EmulatorDetection(
            found=False,
            message="Automatic setup currently supports GBA with VisualBoy Advance only.",
        )

    if emulator_id != "visualboyadvance":
        return EmulatorDetection(
            found=False,
            emulator_id=emulator_id,
            message="That emulator is not supported yet.",
        )

    if IS_MAC:
        return _detect_vba_on_mac()

    return EmulatorDetection(
        found=False,
        emulator_id="visualboyadvance",
        display_name="VisualBoy Advance",
        message="Automatic emulator detection is not implemented on this platform yet.",
    )


VBA_APP_LAUNCH_NAMES = (
    "visualboyadvance-m",
    "VisualBoyAdvance-M",
    "VisualBoyAdvance",
)

# Auto-link uses save-state slot 8 (Shift+F8 / F8) when restarting VBA-M.
CHATPLAYS_VBA_STATE_SLOT = 8

MAC_FUNCTION_KEY_CODES = {
    1: 122,
    2: 120,
    3: 99,
    4: 118,
    5: 96,
    6: 97,
    7: 98,
    8: 100,
    9: 101,
    10: 109,
}


def _escape_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _find_running_vba_process() -> Optional[str]:
    script = """
set output to ""
tell application "System Events"
    repeat with proc in (every application process whose background only is false)
        set procName to name of proc
        if procName contains "visualboyadvance" or procName contains "VisualBoyAdvance" or procName contains "vbam" then
            set output to procName
            exit repeat
        end if
    end repeat
end tell
return output
"""
    raw, _ = _run_osascript(script)
    return raw or None


def _read_vba_recent_rom(config_path: Optional[str] = None) -> Optional[Path]:
    """Return the most recent ROM path VBA-M had open, if the file still exists."""
    path = Path(config_path) if config_path else _find_vbam_config()
    if not path or not path.is_file():
        return None

    recent = _parse_ini_sections(path).get("Recent", {})
    for index in range(1, 11):
        candidate = recent.get(f"file{index}", "").strip()
        if not candidate:
            continue
        rom_path = Path(candidate).expanduser()
        if rom_path.is_file():
            return rom_path
    return None


def _vba_send_function_key(
    process_name: str,
    slot: int,
    *,
    shift: bool = False,
) -> bool:
    key_code = MAC_FUNCTION_KEY_CODES.get(slot)
    if key_code is None:
        return False

    escaped_process = _escape_applescript(process_name)
    shift_clause = " using {shift down}" if shift else ""
    script = f"""
tell application "{escaped_process}" to activate
delay 0.35
tell application "System Events"
    tell process "{escaped_process}"
        set frontmost to true
    end tell
    key code {key_code}{shift_clause}
end tell
"""
    _, error = _run_osascript(script, timeout=OSASCRIPT_UI_TIMEOUT)
    if error:
        logger.warning(
            "Could not send VBA-M function key F%s%s: %s",
            slot,
            " (shift)" if shift else "",
            error,
        )
        return False
    return True


def _vba_save_state(process_name: str, slot: int = CHATPLAYS_VBA_STATE_SLOT) -> bool:
    return _vba_send_function_key(process_name, slot, shift=True)


def _vba_load_state(process_name: str, slot: int = CHATPLAYS_VBA_STATE_SLOT) -> bool:
    return _vba_send_function_key(process_name, slot, shift=False)


def launch_vba_emulator(
    detection: Optional[EmulatorDetection] = None,
    rom_path: Optional[Path] = None,
) -> bool:
    if not IS_MAC:
        return False
    candidates = []
    if detection and detection.app_name:
        candidates.append(detection.app_name)
    candidates.extend(VBA_APP_LAUNCH_NAMES)
    seen: set[str] = set()
    for name in candidates:
        if not name or name in seen:
            continue
        seen.add(name)
        command = ["open", "-a", name]
        if rom_path:
            command.append(str(rom_path))
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return True
    return False


def restart_vba_emulator(
    detection: Optional[EmulatorDetection] = None,
    *,
    preserve_game: bool = False,
    config_path: Optional[str] = None,
) -> tuple[bool, bool]:
    """Restart VBA-M.

    When preserve_game is True and a ROM was open, saves to slot 8 before quit,
    relaunches with that ROM, then loads slot 8. Returns (launched, game_restored).
    """
    if not IS_MAC:
        return False, False

    process_name = _find_running_vba_process()
    if not process_name and detection and detection.found:
        process_name = detection.app_name

    rom_path: Optional[Path] = None
    game_restored = False
    if preserve_game and process_name:
        rom_path = _read_vba_recent_rom(config_path)
        if rom_path:
            if _vba_save_state(process_name):
                time.sleep(0.6)
            else:
                logger.warning(
                    "Could not save VBA-M state before restart; game progress may be lost."
                )
                rom_path = None

    if process_name:
        _run_osascript(f'tell application "{_escape_applescript(process_name)}" to quit')
        time.sleep(0.8)

    if not launch_vba_emulator(detection, rom_path):
        return False, False

    if preserve_game and rom_path:
        time.sleep(2.5)
        process_name = _find_running_vba_process()
        if process_name and _vba_load_state(process_name):
            game_restored = True
            time.sleep(0.6)
        else:
            logger.warning(
                "Relaunched %s but could not restore save state from slot %s.",
                rom_path.name,
                CHATPLAYS_VBA_STATE_SLOT,
            )

    return True, game_restored


def close_vba_joypad_configuration(process_name: Optional[str] = None) -> bool:
    """Dismiss the Joypad Configuration dialog without saving stale UI state."""
    if not IS_MAC:
        return False

    if not process_name:
        process_name = _find_running_vba_process()
    if not process_name:
        return False

    escaped_process = _escape_applescript(process_name)
    script = f"""
tell application "System Events"
    tell process "{escaped_process}"
        if not (exists window "Joypad Configuration") then
            return "none"
        end if
        try
            click button "Cancel" of window "Joypad Configuration"
        on error
            try
                click button 2 of window "Joypad Configuration"
            on error
                keystroke "w" using {{command down}}
            end try
        end try
        return "closed"
    end tell
end tell
"""
    raw, error = _run_osascript(script, timeout=OSASCRIPT_UI_TIMEOUT)
    if error:
        logger.warning("Could not close VBA-M joypad configuration: %s", error)
        return False
    return raw == "closed"


def open_vba_joypad_configuration(detection: Optional[EmulatorDetection] = None) -> bool:
    """Open VBA-M Options > Input > Configure (Joypad Configuration dialog)."""
    if not IS_MAC:
        return False

    process_name = _find_running_vba_process()
    if not process_name and detection and detection.found:
        process_name = detection.app_name

    if not process_name:
        if not launch_vba_emulator(detection):
            return False
        time.sleep(1.5)
        process_name = _find_running_vba_process()

    if not process_name:
        return False

    close_vba_joypad_configuration(process_name)
    time.sleep(0.25)

    escaped_process = _escape_applescript(process_name)
    script = f"""
tell application "{escaped_process}" to activate
delay 0.4
tell application "System Events"
    tell process "{escaped_process}"
        click menu item "Configure..." of menu "Input" of menu item "Input" of menu "Options" of menu bar item "Options" of menu bar 1
    end tell
end tell
"""
    _, error = _run_osascript(script, timeout=OSASCRIPT_UI_TIMEOUT)
    if error:
        logger.warning("Could not open VBA-M joypad configuration: %s", error)
        return False
    return True


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
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
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


def _parse_ini_sections(config_path: Path) -> Dict[str, Dict[str, str]]:
    sections: Dict[str, Dict[str, str]] = {}
    current: Optional[str] = None
    for line in config_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]
            sections.setdefault(current, {})
            continue
        if current and "=" in stripped:
            key, value = stripped.split("=", 1)
            sections[current][key.strip()] = value.strip()
    return sections


def _is_keyboard_binding(value: str) -> bool:
    cleaned = value.strip().lower()
    if not cleaned:
        return False
    if cleaned.startswith("joy"):
        return False
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    if not re.fullmatch(r"[0-9a-f]+", cleaned):
        return False
    return cleaned[0] == "0"


def _vba_config_string_to_chatplays_key(value: str) -> Optional[str]:
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.upper().startswith("JOY"):
        return None
    if len(cleaned) == 1:
        return cleaned.lower()
    return VBA_STRING_TO_CHATPLAYS_KEY.get(cleaned.upper())


def _chatplays_key_to_vba_string(key: str) -> str:
    normalized = key.strip().lower()
    if normalized in CHATPLAYS_KEY_TO_VBA_STRING:
        return CHATPLAYS_KEY_TO_VBA_STRING[normalized]
    if len(normalized) == 1:
        return normalized.upper()
    return normalized.upper()


def _read_modern_joypad_mapping(section: Dict[str, str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for field, input_name in VBA_JOY1_FIELD_TO_INPUT.items():
        raw_value = section.get(field, "")
        key_name = _vba_config_string_to_chatplays_key(raw_value)
        if key_name:
            mapping[input_name] = key_name
    return mapping


def _joypad_section_needs_keyboard_update(section: Dict[str, str]) -> bool:
    for field in VBA_JOY1_CORE_FIELDS:
        raw_value = section.get(field, "").strip()
        if not raw_value:
            return True
        if raw_value.upper().startswith("JOY"):
            return True
        if not _vba_config_string_to_chatplays_key(raw_value):
            return True
    return False


def _joypad1_values_from_mapping(mapping: Dict[str, str]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for field, input_name in VBA_JOY1_FIELD_TO_INPUT.items():
        chatplays_key = mapping.get(input_name, VBA_DEFAULT_KEYBOARD.get(input_name, ""))
        if chatplays_key:
            values[field] = _chatplays_key_to_vba_string(chatplays_key)
    return values


def _update_ini_section_values(config_path: Path, section: str, values: Dict[str, str]) -> None:
    """Replace key/value lines inside an existing ini section."""
    lines = config_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    section_header = f"[{section}]"
    output: list[str] = []
    in_section = False
    updated_keys: set[str] = set()
    section_exists = any(line.strip() == section_header for line in lines)

    for line in lines:
        stripped = line.strip()
        if stripped == section_header:
            in_section = True
            output.append(line)
            continue
        if in_section:
            if stripped.startswith("[") and stripped.endswith("]"):
                for key, value in values.items():
                    if key not in updated_keys:
                        output.append(f"{key}={value}")
                        updated_keys.add(key)
                in_section = False
                output.append(line)
                continue
            if "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in values:
                    output.append(f"{key}={values[key]}")
                    updated_keys.add(key)
                    continue
            output.append(line)
            continue
        output.append(line)

    if in_section:
        for key, value in values.items():
            if key not in updated_keys:
                output.append(f"{key}={value}")
                updated_keys.add(key)

    if not section_exists:
        if output and output[-1].strip():
            output.append("")
        output.append(section_header)
        for key, value in values.items():
            output.append(f"{key}={value}")

    config_path.write_text("\n".join(output) + "\n", encoding="utf-8")


def write_vba_gba_keyboard_map(
    mapping: Optional[Dict[str, str]] = None,
    config_path: Optional[str] = None,
) -> list[Path]:
    """Write keyboard bindings to VBA-M [Joypad/1] in every discovered vbam.ini."""
    target_mapping = dict(VBA_DEFAULT_KEYBOARD)
    if mapping:
        target_mapping.update(mapping)

    values = _joypad1_values_from_mapping(target_mapping)
    updated: list[Path] = []

    if config_path:
        paths = [Path(config_path)]
    else:
        paths = _all_vbam_configs()

    for path in paths:
        if not path.is_file():
            continue
        _update_ini_section_values(path, "Joypad/1", values)
        updated.append(path)

    return updated


def apply_vba_joypad_link(
    mapping: Dict[str, str],
    detection: Optional[EmulatorDetection] = None,
    config_path: Optional[str] = None,
    *,
    reload_config: bool = False,
) -> tuple[bool, bool, bool, bool]:
    """Write joypad bindings and open Configure.

    Returns (config_opened, was_already_running, restarted_emulator, game_restored).
    When reload_config is True and VBA-M is already running, it is restarted so
    cleared or invalid joypad bindings are reloaded from vbam.ini. If a ROM was
    open, its save state is preserved via VBA-M slot 8.
    """
    seen: set[Path] = set()
    for path in _all_vbam_configs():
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        write_vba_gba_keyboard_map(mapping, str(path))

    if config_path:
        path = Path(config_path)
        resolved = path.resolve()
        if resolved not in seen and path.is_file():
            write_vba_gba_keyboard_map(mapping, str(path))

    was_already_running = _find_running_vba_process() is not None
    restarted_emulator = False
    game_restored = False

    if was_already_running:
        process_name = _find_running_vba_process()
        if process_name:
            close_vba_joypad_configuration(process_name)
            time.sleep(0.25)

        if reload_config:
            launched, game_restored = restart_vba_emulator(
                detection,
                preserve_game=True,
                config_path=config_path,
            )
            if not launched:
                return False, True, False, False
            restarted_emulator = True
            time.sleep(1.0)
        else:
            if detection and detection.found:
                focus_emulator(detection)
            elif process_name:
                _run_osascript(
                    f'tell application "{_escape_applescript(process_name)}" to activate'
                )
            time.sleep(0.4)
    else:
        if not launch_vba_emulator(detection):
            return False, False, False, False
        time.sleep(1.5)

    return (
        open_vba_joypad_configuration(detection),
        was_already_running,
        restarted_emulator,
        game_restored,
    )


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
    modern = _vba_config_string_to_chatplays_key(value)
    if modern:
        return modern
    if not _is_keyboard_binding(value):
        return None
    cleaned = value.strip().lower().removeprefix("0x")
    code = int(cleaned, 16)
    # Legacy VBA format is YXXX (device + SDL keysym). Keep the low 12 bits.
    return _sdl_to_key_name(code & 0xFFF)


def read_vba_gba_keyboard_map(config_path: Optional[str] = None) -> tuple[Dict[str, str], str]:
    """Return ChatPlays GBA input names mapped to keyboard key strings."""
    mapping = dict(VBA_DEFAULT_KEYBOARD)
    source = "VBA defaults"

    path = Path(config_path) if config_path else _find_vbam_config()
    if not path or not path.is_file():
        return mapping, source

    sections = _parse_ini_sections(path)
    joy1 = sections.get("Joypad/1")
    if joy1 is not None:
        parsed = _read_modern_joypad_mapping(joy1)
        if parsed:
            mapping.update(parsed)
            source = path.name
        return mapping, source

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


def sync_vba_gba_keyboard(config_path: Optional[str] = None) -> tuple[Dict[str, str], str, bool]:
    """Read VBA joypad bindings, writing keyboard defaults when missing or invalid."""
    path = Path(config_path) if config_path else _find_vbam_config()
    if not path or not path.is_file():
        updated = write_vba_gba_keyboard_map()
        if updated:
            return dict(VBA_DEFAULT_KEYBOARD), f"{updated[0].name} (created)", True
        return dict(VBA_DEFAULT_KEYBOARD), "VBA defaults", False

    sections = _parse_ini_sections(path)
    joy1 = sections.get("Joypad/1")
    if joy1 is not None:
        if _joypad_section_needs_keyboard_update(joy1):
            updated = write_vba_gba_keyboard_map(VBA_DEFAULT_KEYBOARD, str(path))
            for extra_path in _all_vbam_configs():
                if extra_path != path:
                    write_vba_gba_keyboard_map(VBA_DEFAULT_KEYBOARD, str(extra_path))
            label = updated[0].name if updated else path.name
            return dict(VBA_DEFAULT_KEYBOARD), f"{label} (joypad updated)", True

        mapping = dict(VBA_DEFAULT_KEYBOARD)
        mapping.update(_read_modern_joypad_mapping(joy1))
        return mapping, path.name, False

    mapping, source = read_vba_gba_keyboard_map(str(path))
    if source == "VBA defaults":
        updated = write_vba_gba_keyboard_map(VBA_DEFAULT_KEYBOARD, str(path))
        label = updated[0].name if updated else path.name
        return dict(VBA_DEFAULT_KEYBOARD), f"{label} (joypad updated)", True
    return mapping, source, False


def build_auto_link_summary(mapping: Dict[str, str], source: str, *, wrote_config: bool = False) -> str:
    pairs = ", ".join(f"{name}={key}" for name, key in sorted(mapping.items()))
    prefix = "Updated and linked using" if wrote_config else "Linked using"
    return f"{prefix} {source}: {pairs}"
