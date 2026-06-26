"""Headless setup/test logic (no PyQt). Used by the Electron UI via api_server."""

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

from emulator_support import (
    EmulatorDetection,
    build_auto_link_summary,
    focus_emulator,
    read_vba_gba_keyboard_map,
    scan_for_emulator,
)

if IS_MAC:
    from pynput import keyboard as pynput_keyboard

    from keyboard_backend import ANALOG_INPUTS, pynput_key_to_string, write_keyboard_mapping, write_keyboard_mappings
else:
    from keyboard_backend import write_keyboard_mappings

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
    manual_setup_active: bool = False
    manual_setup_prompt: str = ""
    manual_setup_current_input: str = ""
    setup_link_mode: str = "manual"
    emulator_detected: bool = False
    emulator_name: str = ""
    emulator_window: str = ""
    emulator_message: str = ""
    emulator_config_path: str = ""
    auto_link_status: str = ""


class SetupTestService:
    def __init__(self, on_change: Optional[Callable[[SetupTestState], None]] = None):
        self.program = ChatPlays()
        self.on_change = on_change
        self.state = SetupTestState()
        self._lock = threading.Lock()
        self._setup_timer: Optional[threading.Timer] = None
        self._democracy_timer: Optional[threading.Timer] = None
        self._setup_timer_context = {}
        self._manual_setup_inputs: List[str] = []
        self._manual_setup_index = 0
        self._keyboard_listener = None
        self._manual_setup_waiting_for_key = False
        self._emulator_detection = EmulatorDetection(found=False)
        self._sync_from_program()
        self.state.controller = self._controller_label()
        self._refresh_button_map()

        self._anarchy_thread = threading.Thread(
            target=self._run_anarchy_thread, daemon=True
        )
        self._democracy_thread = threading.Thread(
            target=self._run_democracy_thread, daemon=True
        )
        self._anarchy_thread.start()
        self._democracy_thread.start()

    def get_state(self) -> SetupTestState:
        with self._lock:
            return self.state

    def _notify(self):
        if self.on_change:
            self.on_change(self.get_state())

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
            self._cancel_setup_timer()
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
            if normalized == "anarchy":
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
            self.cancel_manual_setup()
        with self._lock:
            self.state.setup_link_mode = normalized
        if normalized == "automatic":
            self.scan_emulator()
        else:
            with self._lock:
                self.state.emulator_detected = False
                self.state.emulator_name = ""
                self.state.emulator_window = ""
                self.state.emulator_message = ""
                self.state.emulator_config_path = ""
                self.state.auto_link_status = ""
            self._notify()

    def scan_emulator(self):
        detection = scan_for_emulator(self.state.controller)
        self._apply_emulator_detection(detection)

    def _apply_emulator_detection(self, detection: EmulatorDetection):
        self._emulator_detection = detection
        with self._lock:
            self.state.emulator_detected = detection.found
            self.state.emulator_name = detection.display_name if detection.found else ""
            self.state.emulator_window = detection.window_title if detection.found else ""
            self.state.emulator_config_path = detection.config_path or ""
            self.state.emulator_message = detection.message
            if not detection.found:
                self.state.auto_link_status = ""
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

        detection = scan_for_emulator(self.state.controller)
        self._apply_emulator_detection(detection)

        config_path = detection.config_path or None
        mapping, source = read_vba_gba_keyboard_map(config_path)
        controller_name = self._controller_class_name()

        write_keyboard_mappings(controller_name, mapping)
        self.program.setupTest.controller.reload_keyboard_mappings()

        if detection.found:
            focus_emulator(detection)

        summary = build_auto_link_summary(mapping, source)
        gov = self.program.setupTest.getMetaGov()
        with self._lock:
            self.state.auto_link_status = summary
            self._append_chat_line("Automatic link complete.", gov)
            self._append_chat_line(summary, gov)
            if detection.found:
                self._append_chat_line(
                    f"Focused emulator window: {detection.window_title}",
                    gov,
                )
            else:
                self._append_chat_line(
                    "Emulator window not focused — open VisualBoy Advance and test inputs.",
                    gov,
                )
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

        with self._lock:
            self._append_chat_line(text, gov)
        self._notify()
        self._start_setup_countdown(single_input=True, button=text)

    def press_controller_button(self, button_name: str):
        if self.state.manual_setup_active:
            return
        mode = self.program.setupTest.getMetaMode()
        if mode == "setup":
            self._start_setup_countdown(single_input=True, button=button_name)
        else:
            self.submit_input(button_name)

    def run_general_setup(self):
        self._start_setup_countdown(single_input=False)

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
        self._cancel_setup_timer()
        with self._lock:
            self.state.manual_setup_active = False
            self.state.manual_setup_prompt = ""
            self.state.manual_setup_current_input = ""
            self._manual_setup_inputs = []
            self._manual_setup_index = 0
            self._manual_setup_waiting_for_key = False
            self._setup_timer_context = {}
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
        with self._lock:
            if not self.state.manual_setup_active:
                return
            if self._manual_setup_index >= len(self._manual_setup_inputs):
                gov = self.program.setupTest.getMetaGov()
                self._append_chat_line("Manual setup complete.", gov)
                self.state.manual_setup_active = False
                self.state.manual_setup_prompt = ""
                self.state.manual_setup_current_input = ""
                self._manual_setup_inputs = []
                self._manual_setup_index = 0
                self._resume_gov_threads()
                self._notify()
                return

            input_name = self._manual_setup_inputs[self._manual_setup_index]
            step = self._manual_setup_index + 1
            total = len(self._manual_setup_inputs)
            self.state.manual_setup_current_input = input_name
            self.program.setupTest.setCountdown(self.state.countdown_seconds)
            self.state.manual_setup_prompt = (
                f"Step {step}/{total}: focus your emulator and bind "
                f'"{input_name}" when it presses.'
            )
            gov = self.program.setupTest.getMetaGov()
            self._append_chat_line(
                f'Pressing "{input_name}" in {self.state.countdown_seconds}s ({step}/{total})',
                gov,
            )

        self._notify()
        self._start_setup_countdown(
            single_input=True,
            button=input_name,
            manual_setup=True,
        )

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
        self._start_setup_countdown(
            single_input=True,
            button=input_name,
            manual_setup=True,
        )

    def _advance_manual_setup(self):
        with self._lock:
            if not self.state.manual_setup_active:
                return
            self._manual_setup_index += 1
        self._begin_manual_setup_step()

    def _start_setup_countdown(
        self,
        single_input: bool,
        button: Optional[str] = None,
        manual_setup: bool = False,
    ):
        gov = self.program.setupTest.getMetaGov()
        with self._lock:
            if not manual_setup:
                self._pause_gov_threads_for_setup()
                self._clear_chat_queue()

            self._setup_timer_context = {
                "single_input": single_input,
                "button": button,
                "gov": gov,
                "manual_setup": manual_setup,
            }
        self._cancel_setup_timer()
        self._schedule_setup_tick()

    def _schedule_setup_tick(self):
        self._setup_timer = threading.Timer(1.0, self._setup_timer_step)
        self._setup_timer.daemon = True
        self._setup_timer.start()

    def _cancel_setup_timer(self):
        if self._setup_timer:
            self._setup_timer.cancel()
            self._setup_timer = None

    def _setup_timer_step(self):
        reschedule = False
        advance_manual = False
        with self._lock:
            count = self.program.setupTest.getCountdown()
            ctx = dict(self._setup_timer_context)
            if count >= 0:
                line = str(count)
                self._append_chat_line(line, ctx.get("gov"))
                self.program.setupTest.reduceSetupCount()
                reschedule = True
            elif ctx.get("single_input"):
                button = ctx.get("button")
                if button:
                    queue = self._chat_queue(ctx.get("gov"))
                    if not queue or queue[-1] != button:
                        self._append_chat_line(button, ctx.get("gov"))
                    input_obj = Input(button, self.program.setupTest)
                    self.program.setupTest.metaCommand(input_obj)
                self.program.setupTest.setCountdown(self.state.countdown_seconds)
                if ctx.get("manual_setup"):
                    self._clear_chat_queue(ctx.get("gov"))
                    self._setup_timer_context = {}
                    advance_manual = True
                else:
                    self._clear_chat_queue(ctx.get("gov"))
                    gov = ctx.get("gov")
                    if gov == "anarchy":
                        self.program.setupTest.setAnarchyThreadStatus(True)
                    else:
                        self.program.setupTest.setDemocracyThreadStatus(True)
                    self._setup_timer_context = {}
            else:
                if not self._run_full_setup_sequence(ctx.get("gov")):
                    self._setup_timer_context = {}

        if reschedule:
            self._notify()
            self._schedule_setup_tick()
            return
        if advance_manual:
            self._notify()
            threading.Timer(0.4, self._advance_manual_setup).start()
            return
        self._notify()

    def _run_full_setup_sequence(self, gov: str) -> bool:
        index = self.program.setupTest.getCountdownIndex()
        inputs = list(self.program.setupTest.controller.getInputs().keys())
        if index < len(inputs):
            current = inputs[index]
            self._append_chat_line(current, gov)
            input_obj = Input(current, self.program.setupTest)
            self.program.setupTest.metaCommand(input_obj)
            if index < len(inputs) - 1:
                self.program.setupTest.setCountdown(self.state.countdown_seconds)
                self.program.setupTest.increaseIndexCount()
                self._setup_timer_context = {"single_input": False, "gov": gov}
                self._schedule_setup_tick()
                return True

            self.program.setupTest.resetIndexCount()
            self.program.setupTest.setCountdown(self.state.countdown_seconds)
            self._clear_chat_queue(gov)
            if gov == "anarchy":
                self.program.setupTest.setAnarchyThreadStatus(True)
            else:
                self.program.setupTest.setDemocracyThreadStatus(True)
        return False

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
                    if not self.state.anarchy_queue:
                        continue
                    text = self.state.anarchy_queue[0]
                    self.program.setupTest.setAnarchyThreadStatus(False)
                input_obj = Input(text, self.program.setupTest)
                self.program.setupTest.metaCommand(input_obj)
                with self._lock:
                    if self.state.anarchy_queue and self.state.anarchy_queue[0] == text:
                        self.state.anarchy_queue.pop(0)
                    self.program.setupTest.setAnarchyThreadStatus(True)
                self._notify()
            except Exception as error:
                logger.exception("Anarchy thread error: %s", error)
                with self._lock:
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
        self._cancel_setup_timer()
        self._cancel_democracy_timer()
