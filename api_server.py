"""HTTP + WebSocket API for the Electron desktop UI."""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from typing import Optional, Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from setup_test_service import SetupTestService, SetupTestState, VoteSlot

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
    government: str = "anarchy"
    program_status: bool = False
    democracy_time_limit: int = 10


class SubmitInputBody(BaseModel):
    text: str


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
    countdown_seconds: Optional[int] = None
    democracy_minutes: Optional[int] = None
    democracy_seconds: Optional[int] = None
    setup_link_mode: Optional[str] = None
    setup_emulator: Optional[str] = None


class MainSettingsBody(BaseModel):
    twitch_username: Optional[str] = None
    government: Optional[str] = None
    democracy_time_limit: Optional[int] = None


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


@app.post("/api/setup/controller-button")
def controller_button(body: ControllerButtonBody):
    service.press_controller_button(body.button)
    return {"ok": True}


@app.post("/api/setup/key-binding")
def update_key_binding(body: KeyBindingBody):
    service.update_key_binding(body.input_name, body.key)
    return {"ok": True}


@app.post("/api/setup/toggle-disabled-input")
def toggle_disabled_input(body: ToggleDisabledBody):
    service.toggle_disabled_input(body.input_name)
    return {"ok": True}


@app.post("/api/setup/scan-emulator")
def scan_emulator():
    service.scan_emulator()
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
    if any(v is not None for v in (body.tap_time, body.press_time, body.hold_time, body.default_time_length)):
        state = service.get_state()
        service.set_time_lengths(
            body.tap_time if body.tap_time is not None else state.tap_time,
            body.press_time if body.press_time is not None else state.press_time,
            body.hold_time if body.hold_time is not None else state.hold_time,
            body.default_time_length if body.default_time_length is not None else state.default_time_length,
        )
    if body.countdown_seconds is not None:
        service.set_countdown(body.countdown_seconds)
    if body.democracy_minutes is not None or body.democracy_seconds is not None:
        state = service.get_state()
        minutes = body.democracy_minutes if body.democracy_minutes is not None else state.democracy_minutes
        seconds = body.democracy_seconds if body.democracy_seconds is not None else state.democracy_seconds
        service.update_democracy_time(minutes, seconds)
    if body.setup_link_mode is not None:
        service.set_setup_link_mode(body.setup_link_mode)
    if body.setup_emulator is not None:
        service.set_setup_emulator(body.setup_emulator)
    return {"ok": True}


@app.post("/api/setup/toggle-mode")
def toggle_setup_mode():
    service.toggle_meta_mode()
    return {"ok": True}


@app.post("/api/main/toggle-power")
def toggle_power():
    main_state.program_status = not main_state.program_status
    service.program.setStatus()
    _schedule_broadcast()
    return {"ok": True, "program_status": main_state.program_status}


@app.post("/api/main/settings")
def update_main_settings(body: MainSettingsBody):
    if body.twitch_username is not None:
        main_state.twitch_username = body.twitch_username
        service.program.setUser(body.twitch_username)
    if body.government is not None:
        main_state.government = body.government.lower()
        service.program.setGov(main_state.government)
        service.set_government(main_state.government)
    if body.democracy_time_limit is not None:
        main_state.democracy_time_limit = body.democracy_time_limit
        service.program.setDemTime(body.democracy_time_limit)
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
