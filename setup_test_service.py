"""Headless setup/test logic (no PyQt). Used by the Electron UI via api_server."""

import copy
import logging
import platform
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from ChatPlays import ChatPlays
from input import Input

logger = logging.getLogger(__name__)

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

from emulator_support import (
    EmulatorDetection,
    IS_WIN,
    build_auto_link_summary,
    apply_vba_joypad_link,
    auto_pick_vba_window_option,
    ensure_vba_emulator_running,
    format_vba_status_message,
    highlight_emulator_window,
    is_automatic_link_compatible,
    resolve_window_selection,
    scan_for_emulator,
    sync_vba_gba_keyboard,
)

if IS_MAC:
    from pynput import keyboard as pynput_keyboard

    from keyboard_backend import ANALOG_INPUTS, load_keyboard_maps, pynput_key_to_string, set_target_process, write_keyboard_mapping, write_keyboard_mappings
else:
    from keyboard_backend import load_keyboard_maps, set_target_process, write_keyboard_mappings
    from virtual_controller_backend import (
        is_valid_virtual_input,
        load_virtual_maps,
        reset_virtual_mappings,
        virtual_input_options_for,
        write_virtual_mapping,
    )

from setup_countdown import SetupCountdownRunner

CONTROLLER_CLASS_NAMES = {
    "GBA": "GBAController",
    "Xbox 360": "XboxController",
    "PlayStation": "PlayStationController",
}


@dataclass
class VoteSlot:
    input_text: str = "empty"
    votes: int = 0


@dataclass
class SetupTestState:
    meta_mode: str = "setup"
    government: str = "anarchy"
    controller: str = "GBA"
    setup_or_test: str = "Setup"
    tap_time: float = 0.3
    press_time: float = 0.5
    hold_time: float = 1.0
    default_time_length: str = "press"
    countdown_seconds: int = 5
    democracy_minutes: int = 0
    democracy_seconds: int = 15
    democracy_timer_running: bool = False
    democracy_countdown_label: str = "Countdown: 0:15"
    latest_winner: str = "None"
    anarchy_queue: List[str] = field(default_factory=list)
    democracy_queue: List[str] = field(default_factory=list)
    setup_log: List[str] = field(default_factory=list)
    vote_slots: List[VoteSlot] = field(
        default_factory=lambda: [VoteSlot() for _ in range(4)]
    )
    button_map: dict = field(default_factory=dict)
    keyboard_map: dict = field(default_factory=dict)
    binding_mode: str = "keyboard"
    virtual_input_options: List[str] = field(default_factory=list)
    disabled_inputs: List[str] = field(default_factory=list)
    manual_setup_active: bool = False
    manual_setup_prompt: str = ""
    manual_setup_current_input: str = ""
    setup_link_mode: str = "automatic"
    setup_emulator: str = "visualboyadvance"
    emulator_detected: bool = False
    emulator_name: str = ""
    emulator_window: str = ""
    emulator_windows: List[str] = field(default_factory=list)
    emulator_window_options: List[dict] = field(default_factory=list)
    emulator_app_name: str = ""
    emulator_message: str = ""
    emulator_config_path: str = ""
    emulator_executable_path: str = ""
    auto_link_status: str = ""
    automatic_link_available: bool = False
    setup_countdown_line: str = ""
    setup_countdown_active: bool = False


class SetupTestService:
    def __init__(self, on_change: Optional[Callable[[SetupTestState], None]] = None):
        self.program = ChatPlays()
        self.on_change = on_change
        self.state = SetupTestState()
        self._lock = threading.Lock()
        self._democracy_timer: Optional[threading.Timer] = None
        self._manual_setup_inputs: List[str] = []
        self._manual_setup_index = 0
        self._keyboard_listener = None
        self._manual_setup_waiting_for_key = False
        self._emulator_detection = EmulatorDetection(found=False)
        self._program_live = False
        self._sync_from_program()
        self.state.controller = self._controller_label()
        self._refresh_button_map()
        self._countdown_runner = SetupCountdownRunner(self)

        self._anarchy_thread = threading.Thread(
            target=self._run_anarchy_thread, daemon=True
        )
        self._democracy_thread = threading.Thread(
            target=self._run_democracy_thread, daemon=True
        )
        self._anarchy_thread.start()
        self._democracy_thread.start()

    def set_program_live(self, live: bool):
        self._program_live = bool(live)

    def on_program_power_changed(self, *, live: bool, prefer_newest_vba: bool = False):
        self._program_live = bool(live)
        if self.state.controller != "GBA":
            self._notify()
            return
        self.scan_emulator(prefer_newest_vba=prefer_newest_vba)
        if not live:
            with self._lock:
                if self.state.automatic_link_available:
                    self.state.setup_link_mode = "automatic"
        self._notify()

    def _refresh_automatic_link_availability(self):
        with self._lock:
            available = is_automatic_link_compatible(
                self.state.controller,
                self.state.setup_emulator,
                self.state.emulator_window,
                self.state.emulator_window_options,
            )
            self.state.automatic_link_available = available
            if self.state.setup_link_mode == "automatic" and not available:
                self.state.setup_link_mode = "manual"

    def get_state(self) -> SetupTestState:
        with self._lock:
            return copy.deepcopy(self.state)

    def _notify(self):
        if self.on_change:
            with self._lock:
                snapshot = copy.deepcopy(self.state)
            self.on_change(snapshot)

    def _sync_from_program(self):
        st = self.program.setupTest
        self.state.meta_mode = st.getMetaMode()
        self.state.government = st.getMetaGov()
        self.state.tap_time = st.getTapTime()
        self.state.press_time = st.getPressTime()
        self.state.hold_time = st.getHoldTime()
        self.state.default_time_length = st.getDefualtTimeLengthStr() or "press"
        self.state.countdown_seconds = st.getCountdown()
        total = st.getMetaDemTime()
        self.state.democracy_minutes = total // 60
        self.state.democracy_seconds = total % 60
        self.state.latest_winner = st.lastDemocracyWinner

    def _refresh_button_map(self):
        self.state.button_map = self.program.setupTest.controller.getButtonsForUiDict()
        controller_name = self._controller_class_name()
        if IS_MAC:
            try:
                maps = load_keyboard_maps()
                self.state.keyboard_map = maps.get(controller_name, {})
            except Exception:
                self.state.keyboard_map = {}
            self.state.binding_mode = "keyboard"
            self.state.virtual_input_options = []
            return

        self.state.keyboard_map = load_virtual_maps().get(controller_name, {})
        self.state.binding_mode = "virtual"
        self.state.virtual_input_options = virtual_input_options_for(self.state.controller)

    def _controller_label(self) -> str:
        name = type(self.program.setupTest.controller).__name__
        return {"GBAController": "GBA", "XboxController": "Xbox 360", "PlayStationController": "PlayStation"}.get(
            name, "GBA"
        )

    def _format_democracy_countdown(self, total_seconds: int) -> str:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        if seconds >= 10:
            return f"Countdown: {minutes}:{seconds}"
        return f"Countdown: {minutes}:0{seconds}"

    def _chat_queue(self, gov: Optional[str] = None):
        government = gov or self.program.setupTest.getMetaGov()
        if government == "democracy":
            return self.state.democracy_queue
        return self.state.anarchy_queue

    def _append_chat_line(self, line: str, gov: Optional[str] = None, *, prepend: bool = False):
        queue = self._chat_queue(gov)
        if prepend:
            queue.insert(0, line)
        else:
            queue.append(line)

    def _clear_chat_queue(self, gov: Optional[str] = None):
        self._chat_queue(gov).clear()

    def countdown_input_names(self) -> List[str]:
        inputs = list(self.program.setupTest.controller.getInputs().keys())
        if IS_MAC:
            return [name for name in inputs if name not in ANALOG_INPUTS]
        return inputs

    def countdown_seconds_value(self) -> int:
        with self._lock:
            return self.state.countdown_seconds

    def countdown_session_begin(self, *, manual: bool):
        with self._lock:
            if not manual:
                self._pause_gov_threads_for_setup()
                self._clear_chat_queue()
            self.state.setup_countdown_active = True
            self.state.setup_countdown_line = ""
            if not manual:
                self.program.setupTest.resetIndexCount()
            self.program.setupTest.setCountdown(self.state.countdown_seconds)
        self._notify()

    def countdown_session_end(self, *, reset_index: bool):
        with self._lock:
            self.state.setup_countdown_active = False
            self.state.setup_countdown_line = ""
            self.program.setupTest.setCountdown(self.state.countdown_seconds)
            if reset_index:
                self.program.setupTest.resetIndexCount()
            if not self.state.manual_setup_active:
                self._resume_gov_threads()
        self._notify()

    def countdown_show_tick(self, button: str, remaining: int):
        line = button if remaining == 0 else f'"{button}" {remaining}'
        with self._lock:
            self.state.setup_countdown_line = line
        self._notify()

    def countdown_fire_input(self, button: str):
        self.program.setupTest.metaCommand(Input(button, self.program.setupTest))

    def countdown_clear_display(self):
        with self._lock:
            self.state.setup_countdown_line = ""
        self._notify()

    def countdown_manual_step_complete(self):
        with self._lock:
            if not self.state.manual_setup_active:
                return
            self._manual_setup_index += 1
        self._begin_manual_setup_step()

    def _execute_test_command(self, text: str):
        try:
            input_obj = Input(text, self.program.setupTest)
            self.program.setupTest.metaCommand(input_obj)
        except Exception as error:
            logger.exception("Failed to execute test command %r: %s", text, error)

    def set_meta_mode(self, mode: str):
        normalized = mode.lower()
        if normalized not in ("setup", "test"):
            return
        if normalized == "test":
            self._countdown_runner.cancel()
            if self.state.manual_setup_active:
                self.cancel_manual_setup()
            else:
                self._resume_gov_threads()
        with self._lock:
            self.program.setupTest.setMetaMode(normalized)
            self.state.meta_mode = normalized
            self.state.setup_or_test = mode.capitalize() if mode.lower() == "setup" else "Test"
        self._notify()

    def toggle_meta_mode(self):
        current = self.program.setupTest.getMetaMode()
        self.set_meta_mode("test" if current == "setup" else "setup")

    def set_government(self, gov: str):
        normalized = gov.lower()
        if normalized not in ("anarchy", "democracy"):
            return
        with self._lock:
            self.program.setupTest.setMetaGov(normalized)
            self.state.government = normalized
            if self.state.setup_countdown_active or self.state.manual_setup_active:
                if normalized == "anarchy":
                    self.program.setupTest.setAnarchyThreadStatus(False)
                    self.program.setupTest.democracyThreadStatus = False
                else:
                    self.program.setupTest.anarchyThreadStatus = False
                    self.program.setupTest.setDemocracyThreadStatus(False)
            elif normalized == "anarchy":
                self.program.setupTest.democracyThreadStatus = False
                self.program.setupTest.anarchyThreadStatus = True
            else:
                self.program.setupTest.anarchyThreadStatus = False
                self.program.setupTest.democracyThreadStatus = True
        self._notify()

    def set_setup_link_mode(self, mode: str):
        normalized = mode.lower()
        if normalized not in ("manual", "automatic"):
            return
        if normalized == "automatic":
            if not is_automatic_link_compatible(
                self.state.controller,
                self.state.setup_emulator,
                self.state.emulator_window,
                self.state.emulator_window_options,
            ):
                return
            self.cancel_manual_setup()
        with self._lock:
            self.state.setup_link_mode = normalized
        if normalized == "automatic":
            self.scan_emulator()
        else:
            with self._lock:
                self.state.auto_link_status = ""
            self._refresh_automatic_link_availability()
            self._notify()
            return
        self._refresh_automatic_link_availability()
        self._notify()

    def scan_emulator(self, *, prefer_newest_vba: bool = False):
        previous = self.state.emulator_window
        detection = scan_for_emulator(
            self.state.controller,
            emulator_id=self.state.setup_emulator,
            selected_window=previous,
        )
        self._apply_emulator_detection(
            detection,
            previous_window=previous,
            prefer_newest_vba=prefer_newest_vba,
        )

    def select_emulator_window(self, window_id: str):
        normalized = window_id.strip()
        if not normalized:
            return
        with self._lock:
            options = list(self.state.emulator_window_options)
            titles = list(self.state.emulator_windows)
        selection = resolve_window_selection(
            normalized,
            known_options=options,
            known_titles=titles,
        )
        if selection is None:
            return
        title = selection["title"]
        app_name = selection.get("app_name") or self.state.emulator_app_name or "visualboyadvance-m.exe"
        with self._lock:
            self.state.emulator_window = selection["id"]
            self.state.emulator_detected = True
            self.state.emulator_app_name = app_name
            self.state.emulator_message = f"Targeting window “{title}”."
        highlight_emulator_window(self.state.emulator_window, title=title, app_name=app_name)
        self._emulator_detection = EmulatorDetection(
            found=True,
            emulator_id=self._emulator_detection.emulator_id or "visualboyadvance",
            display_name=self.state.emulator_name or self._emulator_detection.display_name,
            app_name=app_name,
            window_title=title,
            window_id=self.state.emulator_window,
            windows=list(self.state.emulator_windows),
            window_options=list(self.state.emulator_window_options),
            config_path=self.state.emulator_config_path,
            executable_path=self.state.emulator_executable_path,
            message=self.state.emulator_message,
        )
        set_target_process(app_name)
        self._refresh_automatic_link_availability()
        self._notify()

    def set_setup_emulator(self, emulator_id: str):
        normalized = emulator_id.strip().lower()
        if not normalized:
            return
        with self._lock:
            self.state.setup_emulator = normalized
        if self.state.setup_link_mode == "automatic":
            self.scan_emulator()
        else:
            self._refresh_automatic_link_availability()
            self._notify()

    def _apply_emulator_detection(
        self,
        detection: EmulatorDetection,
        *,
        previous_window: str = "",
        prefer_newest_vba: bool = False,
    ):
        self._emulator_detection = detection
        with self._lock:
            options = list(detection.window_options)
            titles = list(detection.windows)
            if not titles and options:
                titles = [option["title"] for option in options]
            if detection.found and detection.window_title and detection.window_title not in titles:
                titles = [detection.window_title, *titles]
            self.state.emulator_window_options = options
            self.state.emulator_windows = titles
            self.state.emulator_detected = bool(options or titles)
            self.state.emulator_name = detection.display_name if (options or titles) else ""

            keep_previous = False
            if previous_window:
                for option in options:
                    if option["id"] == previous_window or option["title"] == previous_window:
                        keep_previous = True
                        break
                if not keep_previous and resolve_window_selection(previous_window):
                    keep_previous = True

            if options and (len(options) == 1 or prefer_newest_vba or not keep_previous):
                selected_id, _selected_title = auto_pick_vba_window_option(
                    options,
                    previous_window if keep_previous else "",
                    prefer_newest=prefer_newest_vba,
                )
                selected = selected_id
            else:
                selected = detection.window_id or detection.window_title if (options or titles) else ""
                if previous_window and keep_previous:
                    for option in options:
                        if option["id"] == previous_window or option["title"] == previous_window:
                            selected = option["id"]
                            break
                    else:
                        custom = resolve_window_selection(previous_window)
                        if custom:
                            selected = custom["id"]
                            self.state.emulator_app_name = custom.get("app_name") or detection.app_name
                            self.state.emulator_detected = True
                        elif previous_window in titles:
                            selected = previous_window

            self.state.emulator_window = selected
            self.state.emulator_app_name = detection.app_name if (options or titles) else ""
            if self.state.setup_link_mode == "automatic" and options:
                self.state.emulator_message = format_vba_status_message(
                    len(options),
                    config_path=detection.config_path or "",
                )
            elif keep_previous and resolve_window_selection(previous_window):
                custom = resolve_window_selection(previous_window)
                if custom and custom["id"] == selected:
                    self.state.emulator_message = f"Targeting window “{custom['title']}”."
                else:
                    self.state.emulator_message = detection.message
            else:
                self.state.emulator_message = detection.message
            self.state.emulator_config_path = detection.config_path or ""
            self.state.emulator_executable_path = detection.executable_path or ""
            if not options and not titles:
                self.state.auto_link_status = ""
        app_name = self.state.emulator_app_name if self.state.emulator_window else ""
        set_target_process(app_name)
        self._refresh_automatic_link_availability()
        self._notify()

    def auto_link_emulator(self):
        if self.state.setup_link_mode != "automatic":
            return
        if self.state.controller != "GBA":
            with self._lock:
                self.state.auto_link_status = (
                    "Automatic linking currently supports GBA with VisualBoy Advance."
                )
            self._notify()
            return

        with self._lock:
            self._pause_gov_threads_for_setup()

        try:
            detection = scan_for_emulator(
                self.state.controller,
                emulator_id=self.state.setup_emulator,
                selected_window=self.state.emulator_window,
            )
            self._apply_emulator_detection(detection)

            config_path = detection.config_path or None
            mapping, source, wrote_config = sync_vba_gba_keyboard(config_path)
            controller_name = self._controller_class_name()

            if not IS_WIN:
                write_keyboard_mappings(controller_name, mapping)
                self.program.setupTest.controller.reload_keyboard_mappings()

            joypad_opened, was_already_running, restarted, game_restored = apply_vba_joypad_link(
                mapping, detection, config_path, reload_config=wrote_config and not IS_WIN
            )

            summary = build_auto_link_summary(
                mapping, source, wrote_config=wrote_config, virtual_controller=IS_WIN
            )
            if IS_WIN:
                link_intro = (
                    "The ChatPlays virtual controller (ViGEm) is what you are linking to the emulator — "
                    "not your physical gamepad."
                )
                if joypad_opened and restarted:
                    status = (
                        f"{summary}\n{link_intro}\nRestarted VisualBoy Advance-M and opened joypad "
                        "configuration. In VBA-M, assign each GBA button to the virtual Xbox "
                        "controller that ChatPlays creates."
                    )
                elif joypad_opened and was_already_running:
                    status = (
                        f"{summary}\n{link_intro}\nFocused VisualBoy Advance-M and opened joypad "
                        "configuration. In VBA-M, assign each GBA button to the virtual Xbox "
                        "controller that ChatPlays creates."
                    )
                elif joypad_opened:
                    status = (
                        f"{summary}\n{link_intro}\nLaunched VisualBoy Advance-M and opened joypad "
                        "configuration. In VBA-M, assign each GBA button to the virtual Xbox "
                        "controller that ChatPlays creates."
                    )
                elif was_already_running:
                    status = (
                        f"{summary}\n{link_intro}\nFound VisualBoy Advance-M but could not open "
                        "joypad configuration automatically. Open Options → Input → Configure… "
                        "and map each GBA button to the ChatPlays virtual controller."
                    )
                else:
                    status = (
                        f"{summary}\n{link_intro}\nCould not launch or focus VBA-M. Install "
                        "VisualBoy Advance-M, then try again. If it is already open, open "
                        "Options → Input → Configure… and map the ChatPlays virtual controller."
                    )
            elif joypad_opened and restarted and game_restored:
                status = (
                    f"{summary}\nRestarted VisualBoy Advance-M, restored your game from "
                    "save slot 8, and opened joypad configuration."
                )
            elif joypad_opened and restarted:
                status = (
                    f"{summary}\nRestarted VisualBoy Advance-M to reload cleared joypad "
                    "bindings and opened joypad configuration."
                )
            elif joypad_opened and was_already_running:
                status = (
                    f"{summary}\nUpdated vbam.ini, focused VisualBoy Advance-M, "
                    "and opened joypad configuration."
                )
            elif joypad_opened:
                status = (
                    f"{summary}\nLaunched VisualBoy Advance-M and opened joypad configuration."
                )
            elif was_already_running:
                status = (
                    f"{summary}\nUpdated vbam.ini but could not open joypad configuration. "
                    "Grant Accessibility to Cursor/Python."
                )
            else:
                status = (
                    f"{summary}\nCould not open VBA-M joypad configuration. "
                    "Grant Accessibility to Cursor/Python and ensure VBA-M is installed."
                )
            with self._lock:
                self.state.auto_link_status = status
                self.state.setup_log.append("Automatic link complete.")
                self.state.setup_log.append(summary)
        except Exception as error:
            logger.exception("Automatic link failed: %s", error)
            with self._lock:
                self.state.auto_link_status = f"Automatic link failed: {error}"
        finally:
            with self._lock:
                self._resume_gov_threads()
            self._notify()

    def set_controller(self, controller: str):
        self.cancel_manual_setup()
        with self._lock:
            self.program.setupTest.changeController(controller)
            self.state.controller = controller
            self._refresh_button_map()
            if self._democracy_timer and self.state.democracy_timer_running:
                self.program.setupTest.resetVoteList()
                self._reset_dem_votes(ran_out=False)
                self.state.democracy_queue.clear()
        if self.state.setup_link_mode == "automatic":
            self.scan_emulator()
        else:
            self._refresh_automatic_link_availability()
            self._notify()

    def set_time_lengths(self, tap: float, press: float, hold: float, default: str):
        with self._lock:
            self.program.setupTest.setTapTime(tap)
            self.program.setupTest.setPressTime(press)
            self.program.setupTest.setHoldTime(hold)
            self.program.setupTest.setDefaultTimeLength(default)
            self.state.tap_time = tap
            self.state.press_time = press
            self.state.hold_time = hold
            self.state.default_time_length = default
        self._notify()

    def set_countdown(self, seconds: int):
        with self._lock:
            self.program.setupTest.setCountdown(seconds)
            self.state.countdown_seconds = seconds
        self._notify()

    def submit_input(self, text: str):
        text = text.strip().lower()
        if not text:
            return

        if text == "clear":
            with self._lock:
                if self.state.government == "anarchy":
                    self.state.anarchy_queue.clear()
                else:
                    self.state.democracy_queue.clear()
            self._notify()
            return

        inputs = list(self.program.setupTest.controller.getInputs().keys())
        try:
            input_obj = Input(text, self.program.setupTest)
        except Exception:
            return

        if input_obj.getInput() not in inputs:
            return

        mode = self.program.setupTest.getMetaMode()
        gov = self.program.setupTest.getMetaGov()

        if mode == "test":
            with self._lock:
                if gov == "anarchy":
                    self.state.anarchy_queue.append(text)
                else:
                    self.state.democracy_queue.insert(0, text)
            self._notify()
            self._execute_test_command(text)
            return

        self._countdown_runner.start_single(text)

    def press_controller_button(self, button_name: str):
        if self.state.manual_setup_active:
            return
        mode = self.program.setupTest.getMetaMode()
        if mode == "setup":
            self._countdown_runner.start_single(button_name)
        else:
            self.submit_input(button_name)

    def run_general_setup(self):
        self._countdown_runner.start_general()

    def start_manual_setup(self):
        self.cancel_manual_setup()
        inputs = self._manual_setup_input_list()
        if not inputs:
            with self._lock:
                self._append_chat_line("No bindable inputs for this controller.")
            self._notify()
            return

        with self._lock:
            self._pause_gov_threads_for_setup()
            self._clear_chat_queue()
            self.state.manual_setup_active = True
            self._manual_setup_inputs = inputs
            self._manual_setup_index = 0

        self._begin_manual_setup_step()

    def cancel_manual_setup(self):
        self._stop_keyboard_listener()
        self._countdown_runner.cancel()
        with self._lock:
            self.state.manual_setup_active = False
            self.state.manual_setup_prompt = ""
            self.state.manual_setup_current_input = ""
            self._manual_setup_inputs = []
            self._manual_setup_index = 0
            self._manual_setup_waiting_for_key = False
            self.state.setup_countdown_active = False
            self.state.setup_countdown_line = ""
            self._clear_chat_queue()
        self._resume_gov_threads()
        self._notify()

    def _manual_setup_input_list(self) -> List[str]:
        inputs = list(self.program.setupTest.controller.getInputs().keys())
        if IS_MAC:
            return [name for name in inputs if name not in ANALOG_INPUTS]
        return inputs

    def _controller_class_name(self) -> str:
        return CONTROLLER_CLASS_NAMES.get(
            self.state.controller,
            type(self.program.setupTest.controller).__name__,
        )

    def _pause_gov_threads_for_setup(self):
        gov = self.program.setupTest.getMetaGov()
        if gov == "anarchy":
            self.program.setupTest.setAnarchyThreadStatus(False)
        else:
            self.program.setupTest.setDemocracyThreadStatus(False)

    def _resume_gov_threads(self):
        if not self.state.manual_setup_active:
            gov = self.program.setupTest.getMetaGov()
            if gov == "anarchy":
                self.program.setupTest.setAnarchyThreadStatus(True)
            else:
                self.program.setupTest.setDemocracyThreadStatus(True)

    def _begin_manual_setup_step(self):
        completed = False
        input_name = None
        with self._lock:
            if not self.state.manual_setup_active:
                return
            if self._manual_setup_index >= len(self._manual_setup_inputs):
                gov = self.program.setupTest.getMetaGov()
                self._append_chat_line("Manual setup complete.", gov)
                self.state.manual_setup_active = False
                self.state.manual_setup_prompt = ""
                self.state.manual_setup_current_input = ""
                self.state.setup_countdown_active = False
                self.state.setup_countdown_line = ""
                self._manual_setup_inputs = []
                self._manual_setup_index = 0
                self._resume_gov_threads()
                completed = True
            else:
                input_name = self._manual_setup_inputs[self._manual_setup_index]
                step = self._manual_setup_index + 1
                total = len(self._manual_setup_inputs)
                self.state.manual_setup_current_input = input_name
                self.program.setupTest.setCountdown(self.state.countdown_seconds)
                self.state.manual_setup_prompt = (
                    f"Step {step}/{total}: focus your emulator and bind "
                    f'"{input_name}" when it presses.'
                )

        self._notify()
        if completed:
            return
        self._countdown_runner.start_manual_step(input_name)

    def _start_keyboard_listener(self):
        self._stop_keyboard_listener()

        def on_press(key):
            if not self._manual_setup_waiting_for_key:
                return
            key_string = pynput_key_to_string(key)
            self._stop_keyboard_listener()
            threading.Thread(
                target=self._handle_manual_key_captured,
                args=(key_string,),
                daemon=True,
            ).start()
            return False

        self._keyboard_listener = pynput_keyboard.Listener(on_press=on_press)
        self._keyboard_listener.start()

    def _stop_keyboard_listener(self):
        listener = self._keyboard_listener
        self._keyboard_listener = None
        self._manual_setup_waiting_for_key = False
        if listener is not None:
            listener.stop()

    def toggle_disabled_input(self, input_name: str):
        self.program.setupTest.controller.disableInput(input_name)
        with self._lock:
            if input_name in self.state.disabled_inputs:
                self.state.disabled_inputs.remove(input_name)
            else:
                self.state.disabled_inputs.append(input_name)
        self._notify()

    def update_key_binding(self, input_name: str, key_string: str):
        """Update a single binding for the current controller."""
        controller_name = self._controller_class_name()
        value = key_string.strip()
        if not value:
            return
        try:
            if IS_MAC:
                write_keyboard_mapping(controller_name, input_name, value)
                self.program.setupTest.controller.reload_keyboard_mappings()
            else:
                if not is_valid_virtual_input(controller_name, value):
                    return
                if not write_virtual_mapping(controller_name, input_name, value):
                    return
                self.program.setupTest.controller.reload_virtual_mappings()
        except Exception:
            pass
        with self._lock:
            self.state.keyboard_map[input_name] = value
        self._notify()

    def reset_virtual_bindings(self):
        if IS_MAC:
            return
        controller_name = self._controller_class_name()
        reset_virtual_mappings(controller_name)
        self.program.setupTest.controller.reload_virtual_mappings()
        with self._lock:
            self.state.keyboard_map = load_virtual_maps().get(controller_name, {})
        self._notify()

    def _handle_manual_key_captured(self, key_string: str):
        with self._lock:
            if not self.state.manual_setup_active:
                return
            input_name = self._manual_setup_inputs[self._manual_setup_index]
            controller_name = self._controller_class_name()
            write_keyboard_mapping(controller_name, input_name, key_string)
            self.program.setupTest.controller.reload_keyboard_mappings()
            self.state.setup_log.append(f'Mapped "{input_name}" -> {key_string}')
            self.state.manual_setup_prompt = (
                f'Testing "{input_name}" in {self.state.countdown_seconds}s…'
            )
            self.program.setupTest.setCountdown(self.state.countdown_seconds)

        self._notify()
        self._countdown_runner.start_manual_step(input_name)

    def update_democracy_time(self, minutes: int, seconds: int):
        total = (minutes * 60) + seconds
        with self._lock:
            self.program.setupTest.setMetaDemTime(total)
            self.state.democracy_minutes = minutes
            self.state.democracy_seconds = seconds
            self.state.democracy_countdown_label = self._format_democracy_countdown(total)
        self._notify()

    def toggle_democracy_timer(self):
        with self._lock:
            if not self.state.democracy_timer_running:
                self.state.democracy_timer_running = True
                self.state.democracy_queue.clear()
                self._schedule_democracy_tick()
            else:
                self.state.democracy_timer_running = False
                self._cancel_democracy_timer()
                self._reset_dem_votes(ran_out=False)
                self.state.democracy_queue.clear()
        self._notify()

    def _cancel_democracy_timer(self):
        if self._democracy_timer:
            self._democracy_timer.cancel()
            self._democracy_timer = None

    def _schedule_democracy_tick(self):
        self._democracy_timer = threading.Timer(1.0, self._democracy_timer_step)
        self._democracy_timer.daemon = True
        self._democracy_timer.start()

    def _democracy_timer_step(self):
        with self._lock:
            if not self.state.democracy_timer_running:
                return

            dem_time = self.program.setupTest.getMetaDemTime()
            if dem_time >= 0:
                self.state.democracy_countdown_label = self._format_democracy_countdown(dem_time)
                self.program.setupTest.reduceDemocracyCount()
                self._notify()
                self._schedule_democracy_tick()
                return

            minutes = self.state.democracy_minutes
            seconds = self.state.democracy_seconds
            total = (minutes * 60) + seconds
            self.program.setupTest.setMetaDemTime(total)
            self.program.setupTest.resetVoteList()
            winner_text = self.state.vote_slots[0].input_text
            if winner_text and winner_text != "empty":
                try:
                    winner = Input(winner_text, self.program.setupTest)
                    self.program.setupTest.metaCommand(winner)
                except Exception:
                    pass
            self._reset_dem_votes(ran_out=True)
            self.state.democracy_queue.clear()
            self.state.democracy_countdown_label = self._format_democracy_countdown(total)
        self._notify()
        self._schedule_democracy_tick()

    def _reset_dem_votes(self, ran_out: bool):
        if ran_out:
            winner = self.state.vote_slots[0].input_text
            self.program.setupTest.setLastDemocracyWinner(winner)
            self.state.latest_winner = winner
        self.state.vote_slots = [VoteSlot() for _ in range(4)]

    def _update_vote_slots_from_list(self):
        vote_list = self.program.setupTest.getVoteList()
        sorted_inputs = sorted(vote_list, key=lambda key: vote_list[key], reverse=True)
        slots = [VoteSlot() for _ in range(4)]
        for index, input_text in enumerate(sorted_inputs[:4]):
            slots[index] = VoteSlot(input_text=input_text, votes=vote_list[input_text])
        self.state.vote_slots = slots

    def _run_anarchy_thread(self):
        while True:
            try:
                time.sleep(0.05)
                if self.program.setupTest.getMetaMode() == "test":
                    continue
                if not self.program.setupTest.getAnarchyThreadStatus():
                    continue
                if self.program.setupTest.getMetaGov() != "anarchy":
                    continue
                with self._lock:
                    if self.state.manual_setup_active:
                        continue
                    if self.state.setup_countdown_active:
                        continue
                    if not self.state.anarchy_queue:
                        continue
                    text = self.state.anarchy_queue[0]
                    self.program.setupTest.setAnarchyThreadStatus(False)
                try:
                    input_obj = Input(text, self.program.setupTest)
                except ValueError:
                    with self._lock:
                        if self.state.anarchy_queue and self.state.anarchy_queue[0] == text:
                            self.state.anarchy_queue.pop(0)
                        self.program.setupTest.setAnarchyThreadStatus(True)
                    continue
                self.program.setupTest.metaCommand(input_obj)
                with self._lock:
                    if self.state.anarchy_queue and self.state.anarchy_queue[0] == text:
                        self.state.anarchy_queue.pop(0)
                    self.program.setupTest.setAnarchyThreadStatus(True)
                self._notify()
            except Exception as error:
                logger.exception("Anarchy thread error: %s", error)
                with self._lock:
                    if self.state.anarchy_queue:
                        self.state.anarchy_queue.pop(0)
                    self.program.setupTest.setAnarchyThreadStatus(True)

    def _run_democracy_thread(self):
        while True:
            try:
                time.sleep(0.05)
                if not self.program.setupTest.getDemocracyThreadStatus():
                    continue
                if self.program.setupTest.getMetaGov() != "democracy":
                    continue
                if not self.state.democracy_timer_running:
                    continue
                with self._lock:
                    if not self.state.democracy_queue:
                        continue
                    text = self.state.democracy_queue[0]
                    last = self.program.setupTest.getLastDemocracyItem()
                    if text == last:
                        continue
                    self.program.setupTest.setLastDemocracyItem(text)
                self.program.setupTest.adjustVoteList(text)
                with self._lock:
                    self._update_vote_slots_from_list()
                self._notify()
            except Exception:
                continue

    def shutdown(self):
        self.cancel_manual_setup()
        self._countdown_runner.cancel()
        self._cancel_democracy_timer()
