"""Detect emulators and read their controller bindings for automatic setup."""

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

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

VBA_WINDOWS_EXE_NAMES = (
    "visualboyadvance-m.exe",
    "VisualBoyAdvance-M.exe",
    "vbam.exe",
)

VBA_WINDOW_TITLE_KEYWORDS = (
    "visualboyadvance",
    "visual boy advance",
    "vba-m",
)

_JUNK_WINDOW_TITLES = frozenset(
    {
        "Default IME",
        "MSCTFIME UI",
        "Program Manager",
    }
)


@dataclass
class EmulatorWindow:
    title: str
    app_name: str = "visualboyadvance-m.exe"
    hwnd: int = 0


@dataclass
class EmulatorDetection:
    found: bool
    emulator_id: str = ""
    display_name: str = ""
    app_name: str = ""
    window_title: str = ""
    window_id: str = ""
    windows: List[str] = field(default_factory=list)
    window_options: List[dict] = field(default_factory=list)
    config_path: str = ""
    executable_path: str = ""
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


def _vba_windows_install_dirs() -> List[Path]:
    dirs: List[Path] = []
    for env_name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(env_name, "")
        if not base:
            continue
        for folder in (
            "VisualBoyAdvance-M",
            "visualboyadvance-m",
            "VBA-M",
            Path("Programs") / "visualboyadvance-m",
        ):
            dirs.append(Path(base) / folder)
    return dirs


def _iter_vbam_config_candidates() -> Iterator[Path]:
    seen: set[Path] = set()
    for candidate in VBA_CONFIG_CANDIDATES:
        resolved = candidate.resolve()
        if resolved not in seen:
            seen.add(resolved)
            yield candidate

    if IS_WIN:
        for env_name in ("LOCALAPPDATA", "APPDATA"):
            base = os.environ.get(env_name, "")
            if not base:
                continue
            for folder in ("visualboyadvance-m", "VBA-M", "VisualBoyAdvance-M"):
                candidate = Path(base) / folder / "vbam.ini"
                resolved = candidate.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield candidate
        for install_dir in _vba_windows_install_dirs():
            candidate = install_dir / "vbam.ini"
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield candidate


def _find_vbam_config() -> Optional[Path]:
    for candidate in _iter_vbam_config_candidates():
        if candidate.is_file():
            return candidate
    return None


def _all_vbam_configs() -> list[Path]:
    seen: set[Path] = set()
    configs: list[Path] = []
    for candidate in _iter_vbam_config_candidates():
        resolved = candidate.resolve()
        if candidate.is_file() and resolved not in seen:
            seen.add(resolved)
            configs.append(candidate)
    return configs


def _detect_vba_on_mac(selected_window: str = "") -> EmulatorDetection:
    config_path = _find_vbam_config()
    exe_path = resolve_vba_icon_path()
    windows = _list_vba_windows_mac()
    options = build_emulator_window_options(windows)
    titles = [window.title for window in windows]

    if options:
        selected_id, selected_title = pick_window_option(options, selected_window)
        config_note = f" Config: {config_path.name}" if config_path else " Using VBA default keys."
        count_note = f" ({len(options)} window{'s' if len(options) != 1 else ''} found)"
        app_name = next((window.app_name for window in windows if window.title == selected_title), "VisualBoyAdvance-M")
        return EmulatorDetection(
            found=True,
            emulator_id="visualboyadvance",
            display_name="VisualBoy Advance",
            app_name=app_name,
            window_title=selected_title,
            window_id=selected_id,
            windows=titles,
            window_options=options,
            config_path=str(config_path) if config_path else "",
            executable_path=exe_path,
            message=f"Targeting “{selected_title}”.{count_note}{config_note}",
        )

    pgrep_name = _find_vba_process_via_pgrep()
    if pgrep_name or config_path:
        message = "VisualBoy Advance is not running. Open the emulator, then refresh the window list."
        return EmulatorDetection(
            found=False,
            emulator_id="visualboyadvance",
            display_name="VisualBoy Advance",
            config_path=str(config_path) if config_path else "",
            executable_path=exe_path,
            message=message,
        )

    return EmulatorDetection(
        found=False,
        emulator_id="visualboyadvance",
        display_name="VisualBoy Advance",
        executable_path=exe_path,
        message="VisualBoy Advance not found. Launch VBA-M, then refresh the window list.",
    )


def _find_vba_executable() -> Optional[Path]:
    repo_root = Path(__file__).resolve().parent
    for candidate in (
        repo_root / "visualboyadvance-m.exe",
        Path.cwd() / "visualboyadvance-m.exe",
    ):
        if candidate.is_file():
            return candidate.resolve()

    for install_dir in _vba_windows_install_dirs():
        for exe_name in VBA_WINDOWS_EXE_NAMES:
            candidate = install_dir / exe_name
            if candidate.is_file():
                return candidate.resolve()

    for exe_name in VBA_WINDOWS_EXE_NAMES:
        found = shutil.which(exe_name)
        if found:
            return Path(found).resolve()
    return None


def _find_vba_app_bundle_mac() -> Optional[Path]:
    candidates = (
        Path("/Applications/VisualBoyAdvance-M.app"),
        Path("/Applications/VisualBoyAdvance.app"),
        Path("/Applications/vbam.app"),
        Path.home() / "Applications/VisualBoyAdvance-M.app",
        Path.home() / "Applications/VisualBoyAdvance.app",
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def resolve_vba_icon_path() -> str:
    if IS_WIN:
        exe = _find_vba_executable()
        return str(exe) if exe else ""
    if IS_MAC:
        bundle = _find_vba_app_bundle_mac()
        return str(bundle) if bundle else ""
    return ""


def _find_running_vba_process_windows() -> Optional[str]:
    for exe_name in VBA_WINDOWS_EXE_NAMES:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if exe_name.lower() in result.stdout.lower():
            return exe_name
    return None


def _vba_process_pids_windows() -> set[int]:
    pids: set[int] = set()
    for exe_name in VBA_WINDOWS_EXE_NAMES:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode != 0:
            continue
        for line in result.stdout.strip().splitlines():
            parts = [part.strip('"') for part in line.split('","')]
            if len(parts) < 2:
                parts = [part.strip('"') for part in line.split(",")]
            if len(parts) >= 2 and parts[1].isdigit():
                pids.add(int(parts[1]))
    return pids


def _list_vba_windows_windows() -> List[EmulatorWindow]:
    if not IS_WIN:
        return []

    import ctypes
    from ctypes import wintypes

    vba_pids = _vba_process_pids_windows()
    if not vba_pids:
        return []

    user32 = ctypes.windll.user32
    results: List[EmulatorWindow] = []
    seen_hwnds: set[int] = set()
    default_app_name = "visualboyadvance-m.exe"

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        hwnd_value = int(hwnd)
        if hwnd_value in seen_hwnds:
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value not in vba_pids:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title:
            return True
        seen_hwnds.add(hwnd_value)
        results.append(
            EmulatorWindow(
                title=title,
                app_name=default_app_name,
                hwnd=hwnd_value,
            )
        )
        return True

    user32.EnumWindows(callback, 0)
    return results


def _list_vba_windows_mac() -> List[EmulatorWindow]:
    if not IS_MAC:
        return []

    script = """
set output to ""
tell application "System Events"
    repeat with proc in (every application process whose background only is false)
        set procName to name of proc
        if procName contains "visualboyadvance" or procName contains "VisualBoyAdvance" or procName contains "vbam" then
            repeat with win in (every window of proc)
                try
                    set winTitle to name of win
                    if winTitle is not "" then
                        set output to output & procName & "|||" & winTitle & linefeed
                    end if
                end try
            end repeat
        end if
    end repeat
end tell
return output
"""
    raw, _ = _run_osascript(script, timeout=OSASCRIPT_UI_TIMEOUT)
    if not raw:
        pgrep_name = _find_vba_process_via_pgrep()
        if pgrep_name:
            return [EmulatorWindow(title=pgrep_name, app_name=pgrep_name)]
        return []

    windows: List[EmulatorWindow] = []
    for index, line in enumerate(raw.splitlines()):
        if "|||" not in line:
            continue
        app_name, title = line.split("|||", 1)
        app_name = app_name.strip()
        title = title.strip()
        if not title:
            continue
        windows.append(
            EmulatorWindow(
                title=title,
                app_name=app_name or "VisualBoyAdvance-M",
                hwnd=index + 1,
            )
        )
    return windows


def build_emulator_window_options(windows: List[EmulatorWindow]) -> List[dict]:
    title_counts: Dict[str, int] = {}
    for window in windows:
        title_counts[window.title] = title_counts.get(window.title, 0) + 1

    title_index: Dict[str, int] = {}
    options: List[dict] = []
    for index, window in enumerate(windows):
        app_name = window.app_name or "visualboyadvance-m.exe"
        base_label = f"[{app_name}]: {window.title}"
        if title_counts[window.title] > 1:
            title_index[window.title] = title_index.get(window.title, 0) + 1
            label = f"{base_label} ({title_index[window.title]})"
        else:
            label = base_label
        window_id = str(window.hwnd) if window.hwnd else f"{window.app_name}::{window.title}::{index}"
        options.append({"id": window_id, "title": window.title, "label": label})
    return options


def pick_window_option(options: List[dict], selected: str = "") -> tuple[str, str]:
    if not options:
        return "", ""
    if selected:
        for option in options:
            if option["id"] == selected or option["title"] == selected:
                return option["id"], option["title"]
    return options[0]["id"], options[0]["title"]


def _option_by_id(options: List[dict], window_id: str) -> Optional[dict]:
    for option in options:
        if option.get("id") == window_id:
            return option
    return None


def is_automatic_link_compatible(
    controller: str,
    setup_emulator: str,
    emulator_window: str,
    emulator_window_options: Optional[List[dict]] = None,
) -> bool:
    """Automatic controller linking supports GBA + a detected VisualBoy Advance window."""
    if controller != "GBA":
        return False
    if setup_emulator != "visualboyadvance":
        return False
    if not emulator_window:
        return False
    return _option_by_id(emulator_window_options or [], emulator_window) is not None


def _vba_windows_present() -> bool:
    if IS_WIN:
        return bool(_list_vba_windows_windows())
    if IS_MAC:
        return bool(_list_vba_windows_mac())
    return False


def ensure_vba_emulator_running() -> bool:
    """Launch VisualBoy Advance-M with its most recent game when no instance is running."""
    if _vba_windows_present():
        return True
    return launch_vba_emulator(
        EmulatorDetection(found=False, emulator_id="visualboyadvance"),
        _read_vba_recent_rom(),
    )


def auto_pick_vba_window_option(
    options: List[dict],
    selected: str = "",
    *,
    prefer_newest: bool = False,
) -> tuple[str, str]:
    if not options:
        return "", ""
    if len(options) == 1:
        return options[0]["id"], options[0]["title"]
    if selected:
        for option in options:
            if option["id"] == selected or option["title"] == selected:
                return option["id"], option["title"]
    if prefer_newest:
        numeric_options = []
        for option in options:
            try:
                numeric_options.append((int(option["id"]), option))
            except ValueError:
                continue
        if numeric_options:
            _, option = max(numeric_options, key=lambda item: item[0])
            return option["id"], option["title"]
    return options[0]["id"], options[0]["title"]


def format_vba_status_message(
    window_count: int,
    *,
    config_path: str = "",
    running: bool = True,
) -> str:
    if not running or window_count <= 0:
        return "VisualBoy Advance-M is not running."
    if window_count == 1:
        message = "VisualBoy Advance-M ready."
    else:
        message = f"VisualBoy Advance-M ready ({window_count} windows found)."
    if config_path:
        message += f" Config: {Path(config_path).name}"
    return message


def _window_title_for_hwnd(hwnd: int) -> str:
    if not IS_WIN:
        return ""

    import ctypes

    user32 = ctypes.windll.user32
    if not user32.IsWindow(hwnd):
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value.strip()


def _process_exe_for_hwnd(hwnd: int) -> str:
    if not IS_WIN:
        return ""

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return Path(buffer.value).name
    finally:
        kernel32.CloseHandle(handle)
    return ""


def _is_user_visible_window_windows(hwnd: int) -> bool:
    """True when a top-level window is actually shown to the user (Alt+Tab style)."""
    if not IS_WIN:
        return False

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    if not user32.IsWindow(hwnd):
        return False
    if not user32.IsWindowVisible(hwnd):
        return False

    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if (ex_style & WS_EX_TOOLWINDOW) and not (ex_style & WS_EX_APPWINDOW):
        return False

    try:
        dwmapi = ctypes.windll.dwmapi
        cloaked = ctypes.c_int()
        if dwmapi.DwmGetWindowAttribute(
            wintypes.HWND(hwnd),
            14,  # DWMWA_CLOAKED
            ctypes.byref(cloaked),
            ctypes.sizeof(cloaked),
        ) == 0 and cloaked.value:
            return False
    except OSError:
        pass

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    if rect.right - rect.left <= 0 or rect.bottom - rect.top <= 0:
        return False

    class TITLEBARINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_uint),
            ("rcTitleBar", wintypes.RECT),
            ("rgstate", ctypes.c_uint * 6),
        ]

    title_bar = TITLEBARINFO()
    title_bar.cbSize = ctypes.sizeof(TITLEBARINFO)
    if user32.GetTitleBarInfo(hwnd, ctypes.byref(title_bar)):
        if title_bar.rgstate[0] & 0x8000:  # STATE_SYSTEM_INVISIBLE
            return False

    owner = user32.GetWindow(hwnd, 4)  # GW_OWNER
    if owner:
        owner_style = user32.GetWindowLongW(owner, GWL_EXSTYLE)
        if (owner_style & WS_EX_TOOLWINDOW) and not (owner_style & WS_EX_APPWINDOW):
            return False

    return True


def _list_all_windows_windows() -> List[EmulatorWindow]:
    if not IS_WIN:
        return []

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    own_pid = os.getpid()
    results: List[EmulatorWindow] = []
    seen_hwnds: set[int] = set()

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        hwnd_value = int(hwnd)
        if hwnd_value in seen_hwnds:
            return True
        if not _is_user_visible_window_windows(hwnd_value):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == own_pid:
            return True
        title = _window_title_for_hwnd(hwnd_value)
        if not title or title in _JUNK_WINDOW_TITLES:
            return True
        seen_hwnds.add(hwnd_value)
        app_name = _process_exe_for_hwnd(hwnd_value) or "unknown"
        results.append(
            EmulatorWindow(
                title=title,
                app_name=app_name,
                hwnd=hwnd_value,
            )
        )
        return True

    user32.EnumWindows(callback, 0)
    results.sort(key=lambda window: (window.app_name.lower(), window.title.lower()))
    return results


def _list_all_windows_mac() -> List[EmulatorWindow]:
    if not IS_MAC:
        return []

    script = """
set output to ""
tell application "System Events"
    repeat with proc in (every application process whose background only is false)
        set procName to name of proc
        repeat with win in (every window of proc)
            try
                if visible of win then
                    set winTitle to name of win
                    if winTitle is not "" then
                        set output to output & procName & "|||" & winTitle & linefeed
                    end if
                end if
            end try
        end repeat
    end repeat
end tell
return output
"""
    raw, _ = _run_osascript(script, timeout=OSASCRIPT_UI_TIMEOUT)
    if not raw:
        return []

    windows: List[EmulatorWindow] = []
    for index, line in enumerate(raw.splitlines()):
        if "|||" not in line:
            continue
        app_name, title = line.split("|||", 1)
        app_name = app_name.strip()
        title = title.strip()
        if not title:
            continue
        windows.append(
            EmulatorWindow(
                title=title,
                app_name=app_name or "unknown",
                hwnd=index + 1,
            )
        )
    windows.sort(key=lambda window: (window.app_name.lower(), window.title.lower()))
    return windows


def list_all_windows() -> List[dict]:
    """Return user-visible titled windows as picker options."""
    if IS_WIN:
        windows = _list_all_windows_windows()
    elif IS_MAC:
        windows = _list_all_windows_mac()
    else:
        return []
    return build_emulator_window_options(windows)


def resolve_window_selection(
    window_id: str,
    *,
    known_options: Optional[List[dict]] = None,
    known_titles: Optional[List[str]] = None,
) -> Optional[dict]:
    normalized = window_id.strip()
    if not normalized:
        return None

    option = _option_by_id(known_options or [], normalized)
    if option:
        return dict(option)

    for title in known_titles or []:
        if title == normalized:
            return {"id": normalized, "title": title, "label": title, "app_name": ""}

    if IS_WIN:
        try:
            hwnd = int(normalized)
        except ValueError:
            return None
        title = _window_title_for_hwnd(hwnd)
        if not title:
            return None
        app_name = _process_exe_for_hwnd(hwnd) or "unknown"
        return {
            "id": str(hwnd),
            "title": title,
            "label": f"[{app_name}]: {title}",
            "app_name": app_name,
        }

    if IS_MAC and "::" in normalized:
        parts = normalized.split("::", 2)
        if len(parts) >= 2:
            app_name = parts[0].strip()
            title = parts[1].strip()
            if title:
                return {
                    "id": normalized,
                    "title": title,
                    "label": f"[{app_name}]: {title}" if app_name else title,
                    "app_name": app_name,
                }

    if IS_MAC and normalized:
        for window in _list_all_windows_mac():
            candidate_id = f"{window.app_name}::{window.title}::{window.hwnd}"
            if candidate_id == normalized or window.title == normalized:
                return {
                    "id": candidate_id,
                    "title": window.title,
                    "label": f"[{window.app_name}]: {window.title}",
                    "app_name": window.app_name,
                }

    return None


def _highlight_window_mac(title: str, *, app_name: str = "") -> bool:
    if not IS_MAC or not title:
        return False

    escaped_title = _escape_applescript(title)
    if app_name:
        escaped_app = _escape_applescript(app_name)
        script = f"""
tell application "System Events"
    repeat with proc in (every application process whose background only is false)
        if name of proc is "{escaped_app}" then
            repeat with win in (every window of proc)
                try
                    if name of win is "{escaped_title}" then
                        set frontmost of proc to true
                        perform action "AXRaise" of win
                        return "ok"
                    end if
                end try
            end repeat
        end if
    end repeat
end tell
return ""
"""
    else:
        script = f"""
tell application "System Events"
    repeat with proc in (every application process whose background only is false)
        repeat with win in (every window of proc)
            try
                if name of win is "{escaped_title}" then
                    set frontmost of proc to true
                    perform action "AXRaise" of win
                    return "ok"
                end if
            end try
        end repeat
    end repeat
end tell
return ""
"""
    raw, _ = _run_osascript(script, timeout=OSASCRIPT_UI_TIMEOUT)
    return raw == "ok"


def _highlight_vba_window_mac(title: str) -> bool:
    if not IS_MAC or not title:
        return False

    escaped_title = _escape_applescript(title)
    script = f"""
tell application "System Events"
    repeat with proc in (every application process whose background only is false)
        set procName to name of proc
        if procName contains "visualboyadvance" or procName contains "VisualBoyAdvance" or procName contains "vbam" then
            repeat with win in (every window of proc)
                try
                    if name of win is "{escaped_title}" then
                        set frontmost of proc to true
                        perform action "AXRaise" of win
                        return "ok"
                    end if
                end try
            end repeat
        end if
    end repeat
end tell
return ""
"""
    raw, _ = _run_osascript(script, timeout=OSASCRIPT_UI_TIMEOUT)
    return raw == "ok"


def highlight_emulator_window(
    window_id: str = "",
    *,
    title: str = "",
    app_name: str = "",
) -> bool:
    """Bring a window to the front and flash it so the user can identify it."""
    if IS_WIN:
        if window_id:
            try:
                hwnd = int(window_id)
                if _highlight_hwnd_windows(hwnd):
                    return True
            except ValueError:
                pass
        return _focus_vba_window_windows(title or None)

    if not IS_MAC:
        return False

    if not title and window_id and "::" in window_id:
        parts = window_id.split("::", 2)
        if len(parts) >= 2:
            if not app_name:
                app_name = parts[0]
            title = parts[1]

    if not title:
        return False

    if _highlight_window_mac(title, app_name=app_name):
        return True

    return _highlight_vba_window_mac(title)


def _bring_hwnd_to_front(hwnd: int) -> bool:
    import ctypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    if not user32.IsWindow(hwnd):
        return False

    user32.ShowWindow(hwnd, 9)  # SW_RESTORE

    try:
        user32.AllowSetForegroundWindow(0xFFFFFFFF)
    except Exception:
        pass

    foreground = user32.GetForegroundWindow()
    current_thread = kernel32.GetCurrentThreadId()
    foreground_thread = user32.GetWindowThreadProcessId(foreground, None)
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)

    attached_fg = False
    attached_current = False
    if foreground_thread and target_thread and foreground_thread != target_thread:
        attached_fg = bool(user32.AttachThreadInput(foreground_thread, target_thread, True))
    if target_thread and target_thread != current_thread:
        attached_current = bool(user32.AttachThreadInput(current_thread, target_thread, True))

    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)

    if attached_current:
        user32.AttachThreadInput(current_thread, target_thread, False)
    if attached_fg:
        user32.AttachThreadInput(foreground_thread, target_thread, False)

    return True


def _highlight_hwnd_windows(hwnd: int) -> bool:
    import ctypes
    from ctypes import wintypes

    if not _bring_hwnd_to_front(hwnd):
        return False

    user32 = ctypes.windll.user32

    class FLASHWINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("hwnd", wintypes.HWND),
            ("dwFlags", wintypes.DWORD),
            ("uCount", wintypes.UINT),
            ("dwTimeout", wintypes.DWORD),
        ]

    FLASHW_ALL = 0x3
    flash = FLASHWINFO(
        ctypes.sizeof(FLASHWINFO),
        wintypes.HWND(hwnd),
        FLASHW_ALL,
        4,
        0,
    )
    user32.FlashWindowEx(ctypes.byref(flash))
    return True


def _find_vba_window_title_windows() -> str:
    windows = _list_vba_windows_windows()
    return windows[0].title if windows else ""


def _focus_vba_window_windows(
    window_title: Optional[str] = None,
    *,
    hwnd: Optional[int] = None,
) -> bool:
    if not IS_WIN:
        return False

    if hwnd is not None:
        return _highlight_hwnd_windows(hwnd)

    import ctypes

    user32 = ctypes.windll.user32
    matches: list[tuple[int, str]] = []
    vba_pids = _vba_process_pids_windows()

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if vba_pids and pid.value not in vba_pids:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title:
            return True
        if window_title and title != window_title:
            return True
        if not vba_pids:
            lowered = title.lower()
            if not any(keyword in lowered for keyword in VBA_WINDOW_TITLE_KEYWORDS):
                return True
        matches.append((int(hwnd), title))
        return True

    user32.EnumWindows(callback, 0)
    if not matches:
        return False

    hwnd = matches[0][0]
    return _highlight_hwnd_windows(hwnd)


def _win_send_keys(sequence: str) -> bool:
    escaped = sequence.replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        f"[System.Windows.Forms.SendKeys]::SendWait('{escaped}')"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        logger.debug("Windows SendKeys failed: %s", error)
        return False
    if result.returncode != 0:
        logger.debug("Windows SendKeys error: %s", result.stderr.strip())
        return False
    return True


def _detect_vba_on_windows(selected_window: str = "") -> EmulatorDetection:
    config_path = _find_vbam_config()
    exe_path = resolve_vba_icon_path()
    windows = _list_vba_windows_windows()
    options = build_emulator_window_options(windows)
    titles = [window.title for window in windows]

    if options:
        selected_id, selected_title = auto_pick_vba_window_option(options, selected_window)
        app_name = next((window.app_name for window in windows if window.title == selected_title), "visualboyadvance-m.exe")
        return EmulatorDetection(
            found=True,
            emulator_id="visualboyadvance",
            display_name="VisualBoy Advance-M",
            app_name=app_name,
            window_title=selected_title,
            window_id=selected_id,
            windows=titles,
            window_options=options,
            config_path=str(config_path) if config_path else "",
            executable_path=exe_path,
            message=format_vba_status_message(
                len(options),
                config_path=str(config_path) if config_path else "",
            ),
        )

    if config_path or exe_path:
        return EmulatorDetection(
            found=False,
            emulator_id="visualboyadvance",
            display_name="VisualBoy Advance-M",
            config_path=str(config_path) if config_path else "",
            executable_path=exe_path,
            message=(
                "VisualBoy Advance-M is not running. Open the emulator, then refresh the window list."
            ),
        )

    return EmulatorDetection(
        found=False,
        emulator_id="visualboyadvance",
        display_name="VisualBoy Advance-M",
        message=(
            "VisualBoy Advance-M not found. Install VBA-M, then refresh the window list."
        ),
    )


def scan_for_emulator(
    controller_label: str = "GBA",
    emulator_id: str = "visualboyadvance",
    selected_window: str = "",
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
        return _detect_vba_on_mac(selected_window=selected_window)

    if IS_WIN:
        return _detect_vba_on_windows(selected_window=selected_window)

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


def _find_running_vba_process_mac() -> Optional[str]:
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


def _find_running_vba_process() -> Optional[str]:
    if IS_MAC:
        return _find_running_vba_process_mac()
    if IS_WIN:
        return _find_running_vba_process_windows()
    return None


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
    if IS_WIN:
        executable = _find_vba_executable()
        if not executable:
            return False
        command = [str(executable)]
        if rom_path:
            command.append(str(rom_path))
        try:
            subprocess.Popen(command, close_fds=True)
            return True
        except OSError as error:
            logger.warning("Could not launch VBA-M on Windows: %s", error)
            return False

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
    if IS_WIN:
        process_name = _find_running_vba_process_windows()
        rom_path: Optional[Path] = None
        if preserve_game:
            rom_path = _read_vba_recent_rom(config_path)

        if process_name:
            try:
                subprocess.run(
                    ["taskkill", "/IM", process_name, "/T", "/F"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
            except (OSError, subprocess.TimeoutExpired):
                return False, False
            time.sleep(0.8)

        if not launch_vba_emulator(detection, rom_path):
            return False, False
        return True, bool(rom_path)

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
    if IS_WIN:
        if not _focus_vba_window_windows():
            return False
        time.sleep(0.2)
        return _win_send_keys("{ESC}")

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
    if IS_WIN:
        process_name = _find_running_vba_process_windows()
        if not process_name:
            if not launch_vba_emulator(detection):
                return False
            time.sleep(2.0)
            process_name = _find_running_vba_process_windows()
        if not process_name:
            return False

        close_vba_joypad_configuration(process_name)
        time.sleep(0.25)
        if not _focus_vba_window_windows():
            return False
        time.sleep(0.5)
        if not _win_send_keys("%o"):
            return False
        time.sleep(0.35)
        if not _win_send_keys("i"):
            return False
        time.sleep(0.35)
        if not _win_send_keys("c"):
            return False
        return True

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
    if not detection.found and not detection.app_name:
        return False
    if IS_WIN:
        if detection.window_id:
            try:
                if _highlight_hwnd_windows(int(detection.window_id)):
                    return True
            except ValueError:
                pass
        return _focus_vba_window_windows(detection.window_title or None)
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
    if not IS_WIN:
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
                if IS_WIN:
                    _focus_vba_window_windows()
                else:
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
    if IS_WIN:
        path = Path(config_path) if config_path else _find_vbam_config()
        if path and path.is_file():
            mapping, source = read_vba_gba_keyboard_map(str(path))
            return mapping, source, False
        return (
            dict(VBA_DEFAULT_KEYBOARD),
            "Configure the ChatPlays virtual controller in VBA-M joypad settings",
            False,
        )

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


def build_auto_link_summary(
    mapping: Dict[str, str],
    source: str,
    *,
    wrote_config: bool = False,
    virtual_controller: bool = False,
) -> str:
    if virtual_controller:
        if wrote_config:
            return "Updated VisualBoy Advance-M for the ChatPlays virtual controller."
        return "Linking the ChatPlays virtual controller to VisualBoy Advance-M."
    pairs = ", ".join(f"{name}={key}" for name, key in sorted(mapping.items()))
    prefix = "Updated and linked using" if wrote_config else "Linked using"
    return f"{prefix} {source}: {pairs}"
