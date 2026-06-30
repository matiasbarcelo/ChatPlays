"""HTTP + WebSocket API for the Electron desktop UI."""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import List, Optional, Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from setup_test_service import SetupTestService, SetupTestState, VoteSlot

from emulator_support import (
    scan_for_emulator,
    highlight_emulator_window,
    list_all_windows,
    resolve_window_selection,
    ensure_vba_emulator_running,
    auto_pick_vba_window_option,
    format_vba_status_message,
    _vba_windows_present,
)
from keyboard_backend import set_target_process
from main_settings_store import load_main_settings_cache, save_main_settings_cache
from twitch_user_lookup import lookup_streaming_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_HOST = "127.0.0.1"
API_PORT = 8765


def state_to_dict(state: SetupTestState) -> dict:
    data = asdict(state)
    return data


@dataclass
class MainWindowState:
    twitch_username: str = ""
    twitch_username_verified: bool = False
    twitch_display_name: str = ""
    oauth_key: str = ""
    streaming_platform: str = "twitch"
    emulator: str = "visualboyadvance"
    emulator_detected: bool = False
    emulator_name: str = ""
    emulator_window: str = ""
    emulator_windows: List[str] = field(default_factory=list)
    emulator_window_options: List[dict] = field(default_factory=list)
    emulator_app_name: str = ""
    emulator_message: str = ""
    emulator_executable_path: str = ""
    government: str = "anarchy"
    program_status: bool = False
    democracy_time_limit: int = 10


class SubmitInputBody(BaseModel):
    text: str


class FakeChatRollBody(BaseModel):
    count: Optional[int] = 0


class ControllerButtonBody(BaseModel):
    button: str


class KeyBindingBody(BaseModel):
    input_name: str
    key: str


class ToggleDisabledBody(BaseModel):
    input_name: str


class SettingsBody(BaseModel):
    meta_mode: Optional[str] = None
    government: Optional[str] = None
    controller: Optional[str] = None
    tap_time: Optional[float] = None
    press_time: Optional[float] = None
    hold_time: Optional[float] = None
    default_time_length: Optional[str] = None
    timing_tap_enabled: Optional[bool] = None
    timing_press_enabled: Optional[bool] = None
    timing_hold_enabled: Optional[bool] = None
    countdown_seconds: Optional[int] = None
    allow_custom_input_duration: Optional[bool] = None
    max_input_duration: Optional[int] = None
    allow_timing_prefixes: Optional[bool] = None
    allow_input_repeat: Optional[bool] = None
    allow_input_sequences: Optional[bool] = None
    max_input_sequence_length: Optional[int] = None
    democracy_minutes: Optional[int] = None
    democracy_seconds: Optional[int] = None
    setup_link_mode: Optional[str] = None
    setup_emulator: Optional[str] = None
    chat_decides_default_gov: Optional[str] = None
    chat_decides_switch_threshold: Optional[int] = None
    chat_decides_vote_ttl_minutes: Optional[int] = None


class MainSettingsBody(BaseModel):
    twitch_username: Optional[str] = None
    twitch_username_verified: Optional[bool] = None
    twitch_display_name: Optional[str] = None
    oauth_key: Optional[str] = None
    streaming_platform: Optional[str] = None
    emulator: Optional[str] = None
    government: Optional[str] = None
    democracy_time_limit: Optional[int] = None


class SelectEmulatorWindowBody(BaseModel):
    window: str


class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active.discard(websocket)

    async def broadcast(self, message: dict):
        dead = []
        payload = json.dumps(message)
        for connection in self.active:
            try:
                await connection.send_text(payload)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


manager = ConnectionManager()
main_state = MainWindowState()
loop: Optional[asyncio.AbstractEventLoop] = None


def _schedule_broadcast(setup_state: Optional[SetupTestState] = None):
    if loop is None:
        return
    payload = {
        "type": "state",
        "setup": state_to_dict(setup_state if setup_state is not None else service.get_state()),
        "main": asdict(main_state),
    }
    asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)


service = SetupTestService(on_change=_schedule_broadcast)


def _platform_display_name(result: dict, fallback: str = "") -> str:
    if not result.get("found"):
        return ""
    return (result.get("display_name") or result.get("login") or fallback).strip()


def _apply_twitch_username(
    username: str,
    verified: Optional[bool] = None,
    display_name: Optional[str] = None,
):
    username = username.strip()
    main_state.twitch_username = username
    service.program.setUser(username)
    if not username:
        main_state.twitch_username_verified = False
        main_state.twitch_display_name = ""
        return

    if verified is None:
        result = lookup_streaming_user(main_state.streaming_platform, username)
        main_state.twitch_username_verified = bool(result.get("found"))
        main_state.twitch_display_name = _platform_display_name(result, username)
        return

    main_state.twitch_username_verified = verified
    if not verified:
        main_state.twitch_display_name = ""
        return

    if display_name is not None and display_name.strip():
        main_state.twitch_display_name = display_name.strip()
        return

    result = lookup_streaming_user(main_state.streaming_platform, username)
    main_state.twitch_display_name = _platform_display_name(result, username)


def _persist_main_settings_cache():
    save_main_settings_cache(
        {
            "twitch_username": main_state.twitch_username,
            "twitch_username_verified": main_state.twitch_username_verified,
            "twitch_display_name": main_state.twitch_display_name,
            "streaming_platform": main_state.streaming_platform,
        }
    )


def _load_cached_main_settings():
    cached = load_main_settings_cache()
    if not cached:
        return

    platform = str(cached.get("streaming_platform", "") or "twitch").strip() or "twitch"
    main_state.streaming_platform = platform

    username = str(cached.get("twitch_username", "")).strip()
    if not username:
        return

    verified = bool(cached.get("twitch_username_verified"))
    display_name = str(cached.get("twitch_display_name", "")).strip()
    if verified and display_name:
        _apply_twitch_username(username, True, display_name)
    elif "twitch_username_verified" in cached:
        _apply_twitch_username(username, verified, display_name or None)
    else:
        _apply_twitch_username(username)


_load_cached_main_settings()


def _apply_main_emulator_detection(
    detection,
    *,
    previous_window: str = "",
    prefer_newest_vba: bool = False,
):
    options = list(detection.window_options)
    titles = list(detection.windows)
    if not titles and options:
        titles = [option["title"] for option in options]
    if detection.found and detection.window_title and detection.window_title not in titles:
        titles = [detection.window_title, *titles]

    keep_previous = False
    if previous_window:
        for option in options:
            if option["id"] == previous_window or option["title"] == previous_window:
                keep_previous = True
                break
        if not keep_previous and resolve_window_selection(previous_window):
            keep_previous = True

    if options and (len(options) == 1 or prefer_newest_vba or not keep_previous):
        selected, _ = auto_pick_vba_window_option(
            options,
            previous_window if keep_previous else "",
            prefer_newest=prefer_newest_vba,
        )
    else:
        selected = detection.window_id or detection.window_title
        if previous_window and keep_previous:
            for option in options:
                if option["id"] == previous_window or option["title"] == previous_window:
                    selected = option["id"]
                    break
            else:
                custom = resolve_window_selection(previous_window)
                if custom:
                    selected = custom["id"]
                    main_state.emulator_app_name = custom.get("app_name") or detection.app_name
                    main_state.emulator_detected = True
                    main_state.emulator_message = f"Targeting window “{custom['title']}”."
                elif previous_window in titles:
                    selected = previous_window

    main_state.emulator_window_options = options
    main_state.emulator_windows = titles
    main_state.emulator_detected = bool(options or titles) or bool(
        previous_window and resolve_window_selection(previous_window)
    )
    main_state.emulator_name = detection.display_name if (options or titles) else ""
    main_state.emulator_window = selected if (selected or options or titles) else ""
    if not (keep_previous and resolve_window_selection(previous_window)):
        main_state.emulator_app_name = detection.app_name if (options or titles) else ""
        if options and len(options) == 1:
            main_state.emulator_message = format_vba_status_message(
                len(options),
                config_path=detection.config_path or "",
            )
        else:
            main_state.emulator_message = detection.message
    main_state.emulator_executable_path = detection.executable_path or ""
    set_target_process(main_state.emulator_app_name if main_state.emulator_window else "")


def _sync_emulators_for_power_state(*, live: bool):
    launched = False
    if live and not _vba_windows_present():
        launched = ensure_vba_emulator_running()
        if launched:
            time.sleep(2.0)

    service.on_program_power_changed(live=live, prefer_newest_vba=live and launched)

    previous = main_state.emulator_window
    detection = scan_for_emulator(
        "GBA",
        emulator_id=main_state.emulator,
        selected_window=previous,
    )
    _apply_main_emulator_detection(
        detection,
        previous_window=previous,
        prefer_newest_vba=live and launched,
    )


app = FastAPI(title="ChatPlays API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    global loop
    loop = asyncio.get_running_loop()
    _sync_emulators_for_power_state(live=main_state.program_status)
    _schedule_broadcast()


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/state")
def get_full_state():
    return {
        "setup": state_to_dict(service.get_state()),
        "main": asdict(main_state),
    }


@app.post("/api/setup/submit-input")
def submit_input(body: SubmitInputBody):
    service.submit_input(body.text)
    return {"ok": True}


@app.post("/api/setup/fake-chat-roll")
def start_fake_chat_roll(body: FakeChatRollBody):
    service.start_fake_chat_roll(
        count=body.count if body.count is not None else 0,
    )
    return {"ok": True}


@app.post("/api/setup/fake-chat-roll/stop")
def stop_fake_chat_roll():
    service.stop_fake_chat_roll()
    return {"ok": True}


@app.post("/api/setup/controller-button")
def controller_button(body: ControllerButtonBody):
    service.press_controller_button(body.button)
    return {"ok": True}


@app.post("/api/setup/key-binding")
def update_key_binding(body: KeyBindingBody):
    service.update_key_binding(body.input_name, body.key)
    return {"ok": True}


@app.post("/api/setup/reset-virtual-bindings")
def reset_virtual_bindings():
    service.reset_virtual_bindings()
    return {"ok": True}


@app.post("/api/setup/toggle-disabled-input")
def toggle_disabled_input(body: ToggleDisabledBody):
    service.toggle_disabled_input(body.input_name)
    return {"ok": True}


@app.post("/api/setup/scan-emulator")
def scan_emulator():
    service.scan_emulator()
    return {"ok": True}


@app.post("/api/main/scan-emulator")
def scan_main_emulator():
    previous = main_state.emulator_window
    detection = scan_for_emulator(
        "GBA",
        emulator_id=main_state.emulator,
        selected_window=previous,
    )
    _apply_main_emulator_detection(detection, previous_window=previous)
    _schedule_broadcast()
    return {"ok": True}


@app.get("/api/windows")
def list_windows():
    return {"windows": list_all_windows()}


@app.post("/api/main/select-emulator-window")
def select_main_emulator_window(body: SelectEmulatorWindowBody):
    normalized = body.window.strip()
    selection = resolve_window_selection(
        normalized,
        known_options=main_state.emulator_window_options,
        known_titles=main_state.emulator_windows,
    )
    if selection is None:
        return {"ok": False}
    title = selection["title"]
    window_id = selection["id"]
    app_name = selection.get("app_name") or main_state.emulator_app_name or "visualboyadvance-m.exe"
    main_state.emulator_window = window_id
    main_state.emulator_detected = True
    main_state.emulator_app_name = app_name
    main_state.emulator_message = f"Targeting window “{title}”."
    set_target_process(app_name)
    highlight_emulator_window(window_id, title=title, app_name=app_name)
    _schedule_broadcast()
    return {"ok": True}


@app.post("/api/setup/select-emulator-window")
def select_setup_emulator_window(body: SelectEmulatorWindowBody):
    service.select_emulator_window(body.window)
    return {"ok": True}


@app.post("/api/setup/auto-link")
def auto_link_emulator():
    service.auto_link_emulator()
    return {"ok": True}


@app.post("/api/setup/manual-setup")
def manual_setup():
    service.start_manual_setup()
    return {"ok": True}


@app.post("/api/setup/manual-setup/cancel")
def cancel_manual_setup():
    service.cancel_manual_setup()
    return {"ok": True}


@app.post("/api/setup/general-setup")
def general_setup():
    service.run_general_setup()
    return {"ok": True}


@app.post("/api/setup/toggle-democracy-timer")
def toggle_democracy_timer():
    service.toggle_democracy_timer()
    return {"ok": True}


@app.post("/api/setup/settings")
def update_setup_settings(body: SettingsBody):
    if body.meta_mode is not None:
        service.set_meta_mode(body.meta_mode)
    if body.government is not None:
        service.set_government(body.government)
    if body.controller is not None:
        service.set_controller(body.controller)
    if any(
        v is not None
        for v in (
            body.tap_time,
            body.press_time,
            body.hold_time,
            body.default_time_length,
            body.timing_tap_enabled,
            body.timing_press_enabled,
            body.timing_hold_enabled,
        )
    ):
        state = service.get_state()
        service.set_time_lengths(
            body.tap_time if body.tap_time is not None else state.tap_time,
            body.press_time if body.press_time is not None else state.press_time,
            body.hold_time if body.hold_time is not None else state.hold_time,
            body.default_time_length if body.default_time_length is not None else state.default_time_length,
            body.timing_tap_enabled
            if body.timing_tap_enabled is not None
            else state.timing_tap_enabled,
            body.timing_press_enabled
            if body.timing_press_enabled is not None
            else state.timing_press_enabled,
            body.timing_hold_enabled
            if body.timing_hold_enabled is not None
            else state.timing_hold_enabled,
        )
    if body.countdown_seconds is not None:
        service.set_countdown(body.countdown_seconds)
    if any(
        v is not None
        for v in (
            body.allow_custom_input_duration,
            body.max_input_duration,
            body.allow_timing_prefixes,
            body.allow_input_repeat,
            body.allow_input_sequences,
            body.max_input_sequence_length,
        )
    ):
        state = service.get_state()
        service.set_chat_input_policy(
            body.allow_timing_prefixes
            if body.allow_timing_prefixes is not None
            else state.allow_timing_prefixes,
            body.allow_input_repeat
            if body.allow_input_repeat is not None
            else state.allow_input_repeat,
            body.allow_custom_input_duration
            if body.allow_custom_input_duration is not None
            else state.allow_custom_input_duration,
            body.max_input_duration
            if body.max_input_duration is not None
            else state.max_input_duration,
            body.allow_input_sequences
            if body.allow_input_sequences is not None
            else state.allow_input_sequences,
            body.max_input_sequence_length
            if body.max_input_sequence_length is not None
            else state.max_input_sequence_length,
        )
    if body.democracy_minutes is not None or body.democracy_seconds is not None:
        state = service.get_state()
        minutes = body.democracy_minutes if body.democracy_minutes is not None else state.democracy_minutes
        seconds = body.democracy_seconds if body.democracy_seconds is not None else state.democracy_seconds
        service.update_democracy_time(minutes, seconds)
    if body.setup_link_mode is not None:
        service.set_setup_link_mode(body.setup_link_mode)
    if body.setup_emulator is not None:
        service.set_setup_emulator(body.setup_emulator)
    if any(
        v is not None
        for v in (
            body.chat_decides_default_gov,
            body.chat_decides_switch_threshold,
            body.chat_decides_vote_ttl_minutes,
        )
    ):
        state = service.get_state()
        service.set_chat_decides_settings(
            body.chat_decides_default_gov
            if body.chat_decides_default_gov is not None
            else state.chat_decides_default_gov,
            body.chat_decides_switch_threshold
            if body.chat_decides_switch_threshold is not None
            else state.chat_decides_switch_threshold,
            body.chat_decides_vote_ttl_minutes
            if body.chat_decides_vote_ttl_minutes is not None
            else state.chat_decides_vote_ttl_minutes,
            apply_default=body.chat_decides_default_gov is not None,
        )
    return {"ok": True}


@app.post("/api/setup/toggle-mode")
def toggle_setup_mode():
    service.toggle_meta_mode()
    return {"ok": True}


@app.post("/api/main/toggle-power")
def toggle_power():
    main_state.program_status = not main_state.program_status
    service.program.setStatus()
    _sync_emulators_for_power_state(live=main_state.program_status)
    _schedule_broadcast()
    return {"ok": True, "program_status": main_state.program_status}


@app.get("/api/main/verify-username")
def verify_username(username: str, platform: str = "twitch"):
    return lookup_streaming_user(platform, username)


@app.post("/api/main/settings")
def update_main_settings(body: MainSettingsBody):
    if body.twitch_username is not None:
        _apply_twitch_username(
            body.twitch_username,
            body.twitch_username_verified,
            body.twitch_display_name,
        )
    elif body.twitch_username_verified is not None:
        main_state.twitch_username_verified = (
            body.twitch_username_verified and bool(main_state.twitch_username.strip())
        )
        if not main_state.twitch_username_verified:
            main_state.twitch_display_name = ""
        elif body.twitch_display_name is not None:
            main_state.twitch_display_name = body.twitch_display_name.strip()
    elif body.twitch_display_name is not None and main_state.twitch_username_verified:
        main_state.twitch_display_name = body.twitch_display_name.strip()
    if body.oauth_key is not None:
        main_state.oauth_key = body.oauth_key
    if body.streaming_platform is not None:
        main_state.streaming_platform = body.streaming_platform
        if main_state.twitch_username.strip():
            result = lookup_streaming_user(
                main_state.streaming_platform, main_state.twitch_username
            )
            main_state.twitch_username_verified = bool(result.get("found"))
            main_state.twitch_display_name = _platform_display_name(
                result, main_state.twitch_username
            )
    if body.emulator is not None:
        main_state.emulator = body.emulator
    if body.government is not None:
        main_state.government = body.government.lower()
        service.program.setGov(main_state.government)
        service.set_government(main_state.government)
    if body.democracy_time_limit is not None:
        main_state.democracy_time_limit = body.democracy_time_limit
        service.program.setDemTime(body.democracy_time_limit)
    if any(
        field is not None
        for field in (
            body.twitch_username,
            body.twitch_username_verified,
            body.twitch_display_name,
            body.streaming_platform,
        )
    ):
        _persist_main_settings_cache()
    _schedule_broadcast()
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "state",
                    "setup": state_to_dict(service.get_state()),
                    "main": asdict(main_state),
                }
            )
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.on_event("shutdown")
def on_shutdown():
    service.shutdown()


def main():
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")


if __name__ == "__main__":
    main()
