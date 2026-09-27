"""Headless setup/test logic (no PyQt). Used by the Electron UI via api_server."""

import copy
import logging
import platform
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, List, Optional, Tuple

from ChatPlays import ChatPlays
from input import Input, InputSequence, MAX_MESSAGE_SECONDS, WAIT_INPUT

logger = logging.getLogger(__name__)

DEMOCRACY_LEADER_SLOTS = 7
CHAT_DECIDES_MODE = "chat_decides"
GOVERNANCE_VOTE_CHOICES = ("anarchy", "democracy")
FAKE_CHAT_DURATIONS = (0.5, 1, 1.5, 2, 3, 5, 10)

# Chat panel looks, selectable in Setup/Test and mirrored by the OBS overlay.
CHAT_THEMES = ("dark", "light")

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


class ChatLine(str):
    """A queued chat line that remembers who sent it.

    It is still a str, so every queue comparison and InputSequence parse keeps
    working unchanged; lines typed in the sandbox are plain str with no sender.
    """

    user: str = ""


def _chat_line(text: str, user: str = "") -> str:
    if not user:
        return text
    line = ChatLine(text)
    line.user = user
    return line


@dataclass
class VoteSlot:
    input_text: str = "empty"
    votes: int = 0


# Matches the inter-press wait in Controller.pressButton.
REPEAT_GAP_SECONDS = 0.1


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
    timing_tap_enabled: bool = True
    timing_press_enabled: bool = True
    timing_hold_enabled: bool = True
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
        default_factory=lambda: [VoteSlot() for _ in range(DEMOCRACY_LEADER_SLOTS)]
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
    executing_input: str = ""
    executing_button: str = ""
    executing_button_duration: float = 0.0
    executing_button_repeat: int = 1
    executing_button_seq: int = 0
    fake_chat_running: bool = False
    allow_custom_input_duration: bool = False
    max_input_duration: int = 15
    allow_timing_prefixes: bool = True
    allow_input_repeat: bool = True
    allow_input_sequences: bool = False
    max_input_sequence_length: int = 3
    # A message's total run time is capped at max(this, max_input_duration).
    max_message_seconds: int = MAX_MESSAGE_SECONDS
    chat_decides_default_gov: str = "anarchy"
    chat_decides_switch_threshold: int = 75
    chat_decides_vote_ttl_minutes: int = 5
    chat_decides_active_gov: str = "anarchy"
    chat_decides_anarchy_votes: int = 0
    chat_decides_democracy_votes: int = 0
    chat_decides_democracy_percent: float = 50.0
    chat_decides_last_vote: str = ""

    # Chat panel appearance, shared with the OBS overlay so both match exactly.
    chat_theme: str = "dark"
    # Scrollback buffer, not a display limit — the panel shows what fits and
    # keeps the rest as history. This is only a memory guard so a long stream
    # can't grow the queue without bound; the oldest line is popped off the top.
    chat_queue_max_lines: int = 200


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
        self.program.setupTest.setInputObserver(self._on_input_fired)
        self._sync_from_program()
        self.state.controller = self._controller_label()
        self._refresh_button_map()
        self._countdown_runner = SetupCountdownRunner(self)
        self._pending_democracy_votes: Deque[Tuple[int, str]] = deque()
        self._democracy_vote_serial = 0
        self._chat_decides_gov_votes: Deque[Tuple[float, str]] = deque()
        self._chat_decides_gov_pending: Deque[Tuple[float, str]] = deque()
        self._chat_decides_prune_timer: Optional[threading.Timer] = None

        self._anarchy_thread = threading.Thread(
            target=self._run_anarchy_thread, daemon=True
        )
        self._democracy_thread = threading.Thread(
            target=self._run_democracy_thread, daemon=True
        )
        self._test_queue_thread = threading.Thread(
            target=self._run_test_queue_processor, daemon=True
        )
        self._anarchy_thread.start()
        self._democracy_thread.start()
        self._test_queue_thread.start()

    def set_program_live(self, live: bool):
        self._program_live = bool(live)

    def on_program_power_changed(self, *, live: bool, prefer_newest_vba: bool = False):
        self._program_live = bool(live)
        if live:
            # Live chat is played through Test mode's queue, the same path the
            # sandbox and fake chat use.
            if self.state.meta_mode != "test":
                self.set_meta_mode("test")
            with self._lock:
                if self._effective_government() == "democracy" and not self.state.democracy_timer_running:
                    self._begin_democracy_vote_round()
        else:
            self._stop_democracy_vote_round()
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

    def _on_input_fired(self, input_name, duration, repeat):
        """Observer for SetupTestClass.metaCommand — records the button that is
        pressed right now so the UI and the OBS overlay can animate it."""
        with self._lock:
            if input_name:
                try:
                    repeat_count = max(1, int(repeat or 1))
                except (TypeError, ValueError):
                    repeat_count = 1
                # Controller.pressButton repeats with a 0.1s gap between presses,
                # so the highlight lasts as long as the button is really held.
                held = (float(duration or 0) * repeat_count) + (
                    REPEAT_GAP_SECONDS * (repeat_count - 1)
                )
                self.state.executing_button = input_name
                self.state.executing_button_duration = held
                self.state.executing_button_repeat = repeat_count
                self.state.executing_button_seq += 1
            else:
                self.state.executing_button = ""
                self.state.executing_button_duration = 0.0
                self.state.executing_button_repeat = 1
        self._notify()

    def _sync_from_program(self):
        st = self.program.setupTest
        self.state.meta_mode = st.getMetaMode()
        self.state.government = st.getMetaGov()
        self.state.tap_time = st.getTapTime()
        self.state.press_time = st.getPressTime()
        self.state.hold_time = st.getHoldTime()
        self.state.default_time_length = st.getDefualtTimeLengthStr() or "press"
        self.state.timing_tap_enabled = st.timingTapEnabled
        self.state.timing_press_enabled = st.timingPressEnabled
        self.state.timing_hold_enabled = st.timingHoldEnabled
        self.state.countdown_seconds = st.getCountdown()
        total = st.getMetaDemTime()
        self.state.democracy_minutes = total // 60
        self.state.democracy_seconds = total % 60
        self.state.latest_winner = st.lastDemocracyWinner
        self.state.allow_custom_input_duration = st.getAllowCustomInputDuration()
        self.state.max_input_duration = st.getMaxTimeLength()
        self.state.allow_timing_prefixes = st.getAllowTimingPrefixes()
        self.state.allow_input_repeat = st.getAllowInputRepeat()
        self.state.allow_input_sequences = st.getAllowInputSequences()
        self.state.max_input_sequence_length = st.getMaxInputSequenceLength()

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

    def _is_chat_decides_mode(self) -> bool:
        return self.state.government == CHAT_DECIDES_MODE

    def _effective_government(self) -> str:
        if self._is_chat_decides_mode():
            return self.state.chat_decides_active_gov
        return self.state.government

    def _apply_sub_government_threads(self, sub_gov: str):
        if sub_gov == "anarchy":
            self.program.setupTest.democracyThreadStatus = False
            self.program.setupTest.anarchyThreadStatus = True
        else:
            self.program.setupTest.anarchyThreadStatus = False
            self.program.setupTest.democracyThreadStatus = True

    def _format_democracy_countdown(self, total_seconds: int) -> str:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        if seconds >= 10:
            return f"Countdown: {minutes}:{seconds}"
        return f"Countdown: {minutes}:0{seconds}"

    def _chat_queue(self, gov: Optional[str] = None):
        government = gov or self._effective_government()
        if government == "democracy":
            return self.state.democracy_queue
        return self.state.anarchy_queue

    def _append_chat_line(
        self, line: str, gov: Optional[str] = None, *, prepend: bool = False, user: str = ""
    ):
        line = _chat_line(line, user)
        queue = self._chat_queue(gov)
        if prepend:
            queue.insert(0, line)
        else:
            queue.append(line)
        # Bounded scrollback, not a visible-line limit: drop the oldest line
        # once the queue overflows. Oldest sits at the tail when prepending
        # (newest first, e.g. democracy) and at the head otherwise (oldest
        # first, e.g. anarchy's play queue), so trim whichever end that is.
        max_lines = self.state.chat_queue_max_lines
        if max_lines and max_lines > 0 and len(queue) > max_lines:
            if prepend:
                del queue[max_lines:]
            else:
                del queue[: len(queue) - max_lines]

    def set_chat_theme(self, theme: str):
        if theme not in CHAT_THEMES:
            return
        with self._lock:
            self.state.chat_theme = theme
        self._notify()

    def _clear_chat_queue(self, gov: Optional[str] = None):
        self._chat_queue(gov).clear()

    def _clear_democracy_chat(self):
        self.state.democracy_queue.clear()
        self._pending_democracy_votes.clear()

    def _enqueue_democracy_vote(self, text: str, user: str = ""):
        self._democracy_vote_serial += 1
        self._pending_democracy_votes.append((self._democracy_vote_serial, text))
        self._append_chat_line(text, prepend=True, user=user)

    def _cancel_chat_decides_prune_timer(self):
        if self._chat_decides_prune_timer:
            self._chat_decides_prune_timer.cancel()
            self._chat_decides_prune_timer = None

    def _schedule_chat_decides_prune(self):
        self._cancel_chat_decides_prune_timer()
        if not self._is_chat_decides_mode():
            return
        self._chat_decides_prune_timer = threading.Timer(1.0, self._chat_decides_prune_step)
        self._chat_decides_prune_timer.daemon = True
        self._chat_decides_prune_timer.start()

    def _chat_decides_prune_step(self):
        if self._is_chat_decides_mode():
            self._prune_and_recompute_chat_decides()
            self._schedule_chat_decides_prune()

    def _enqueue_chat_decides_governance_vote(self, choice: str, user: str = ""):
        now = time.time()
        with self._lock:
            self._chat_decides_gov_pending.append((now, choice))
            self._append_chat_line(choice, user=user)
        self._prune_and_recompute_chat_decides(notify=True)

    def _process_chat_decides_gov_queue(self, now: float):
        ttl = max(60, int(self.state.chat_decides_vote_ttl_minutes) * 60)
        queue = self._chat_queue()
        while self._chat_decides_gov_pending:
            timestamp, choice = self._chat_decides_gov_pending[0]
            if now - timestamp > ttl:
                self._chat_decides_gov_pending.popleft()
                if queue and queue[0] == choice:
                    queue.pop(0)
                continue
            if not queue or queue[0] != choice:
                break
            self._chat_decides_gov_votes.append((now, choice))
            self.state.chat_decides_last_vote = choice
            self._chat_decides_gov_pending.popleft()
            queue.pop(0)
            break

    def _prune_and_recompute_chat_decides(self, *, notify: bool = False):
        now = time.time()
        previous = None
        new_active = None
        with self._lock:
            self._process_chat_decides_gov_queue(now)
            ttl = max(60, int(self.state.chat_decides_vote_ttl_minutes) * 60)
            while self._chat_decides_gov_votes and self._chat_decides_gov_votes[0][0] < now - ttl:
                self._chat_decides_gov_votes.popleft()

            applied_vote_events = list(self._chat_decides_gov_votes)
            anarchy = sum(1 for _t, choice in applied_vote_events if choice == "anarchy")
            democracy = sum(1 for _t, choice in applied_vote_events if choice == "democracy")
            self.state.chat_decides_anarchy_votes = anarchy
            self.state.chat_decides_democracy_votes = democracy

            previous = self.state.chat_decides_active_gov
            threshold = max(51, min(int(self.state.chat_decides_switch_threshold), 99))
            lower_bound = 100 - threshold

            if not applied_vote_events:
                democracy_percent = 50.0
                new_active = self.state.chat_decides_default_gov
            else:
                total_votes = democracy + anarchy
                democracy_percent = (democracy / total_votes) * 100.0
                if democracy_percent >= threshold:
                    new_active = "democracy"
                elif democracy_percent <= lower_bound:
                    new_active = "anarchy"
                else:
                    new_active = self.state.chat_decides_default_gov

            self.state.chat_decides_democracy_percent = democracy_percent
            self.state.chat_decides_active_gov = new_active

        if new_active != previous:
            self._on_chat_decides_active_gov_changed(previous, new_active)
            notify = True
        if notify:
            self._notify()

    def _on_chat_decides_active_gov_changed(self, old_gov: str, new_gov: str):
        with self._lock:
            if not self.state.setup_countdown_active and not self.state.manual_setup_active:
                self._apply_sub_government_threads(new_gov)
            if old_gov == "democracy" and new_gov == "anarchy":
                self.state.democracy_timer_running = False
                self._cancel_democracy_timer()
                self._clear_democracy_chat()
                self.program.setupTest.resetVoteList()
                self.state.vote_slots = [VoteSlot() for _ in range(DEMOCRACY_LEADER_SLOTS)]
            elif old_gov == "anarchy" and new_gov == "democracy":
                if self.state.meta_mode == "test" and not self.state.democracy_timer_running:
                    self._begin_democracy_vote_round()

    def _clear_chat_decides_governance_votes(self):
        self._chat_decides_gov_votes.clear()
        self._chat_decides_gov_pending.clear()
        for queue in (self.state.anarchy_queue, self.state.democracy_queue):
            queue[:] = [item for item in queue if item not in GOVERNANCE_VOTE_CHOICES]
        self.state.chat_decides_anarchy_votes = 0
        self.state.chat_decides_democracy_votes = 0
        self.state.chat_decides_democracy_percent = 50.0
        self.state.chat_decides_last_vote = ""

    def _stop_democracy_vote_round(self):
        with self._lock:
            if not self.state.democracy_timer_running:
                return
            self.state.democracy_timer_running = False
            self._cancel_democracy_timer()
            self._reset_dem_votes(ran_out=False)
            self._clear_democracy_chat()
            total = (self.state.democracy_minutes * 60) + self.state.democracy_seconds
            self.program.setupTest.setMetaDemTime(total)
            self.state.democracy_countdown_label = self._format_democracy_countdown(total)

    def _apply_chat_decides_default_start(self):
        with self._lock:
            previous = self.state.chat_decides_active_gov
            new_active = self.state.chat_decides_default_gov
            self._clear_chat_decides_governance_votes()
            self.state.chat_decides_active_gov = new_active
            self.state.chat_decides_democracy_percent = 50.0
        if previous != new_active:
            self._on_chat_decides_active_gov_changed(previous, new_active)
        else:
            with self._lock:
                if new_active == "democracy":
                    self._stop_democracy_vote_round()
                    self.program.setupTest.resetVoteList()
                    self.state.vote_slots = [VoteSlot() for _ in range(DEMOCRACY_LEADER_SLOTS)]
        self._notify()

    def set_chat_decides_settings(
        self,
        default_gov: str,
        switch_threshold: int,
        vote_ttl_minutes: int,
        *,
        apply_default: bool = False,
    ):
        default = default_gov.lower() if default_gov.lower() in GOVERNANCE_VOTE_CHOICES else "anarchy"
        threshold = max(51, min(int(switch_threshold), 99))
        ttl_minutes = max(1, min(int(vote_ttl_minutes), 1440))
        default_changed = False
        with self._lock:
            default_changed = default != self.state.chat_decides_default_gov
            self.state.chat_decides_default_gov = default
            self.state.chat_decides_switch_threshold = threshold
            self.state.chat_decides_vote_ttl_minutes = ttl_minutes
        if self._is_chat_decides_mode() and (default_changed or apply_default):
            self._apply_chat_decides_default_start()
        elif self._is_chat_decides_mode():
            self._prune_and_recompute_chat_decides(notify=True)
        else:
            self._notify()

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
        self._execute_chat_command(button)

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

    def _execute_chat_command(self, text: str):
        try:
            command = InputSequence(text, self.program.setupTest)
            self.program.setupTest.metaCommand(command)
        except Exception as error:
            logger.exception("Failed to execute chat command %r: %s", text, error)

    def _is_valid_chat_command(self, text: str) -> bool:
        try:
            command = InputSequence(text, self.program.setupTest)
        except Exception:
            return False

        controller_inputs = set(self.program.setupTest.controller.getInputs().keys())
        disabled = set(self.state.disabled_inputs)
        for input_obj in command.getInputs():
            name = input_obj.getInput()
            if name == WAIT_INPUT:
                continue
            if name not in controller_inputs or name in disabled:
                return False
        return True

    def _valid_test_inputs(self) -> List[str]:
        inputs = list(self.program.setupTest.controller.getInputs().keys())
        disabled = set(self.state.disabled_inputs)
        available = [name for name in inputs if name not in disabled]
        available.append(WAIT_INPUT)
        if self._is_chat_decides_mode():
            available.extend(GOVERNANCE_VOTE_CHOICES)
        return available

    def _peek_next_test_queue_item(self) -> Optional[str]:
        queue = self._chat_queue()
        if not queue:
            return None
        return queue[0]

    def _remove_test_queue_item(self, text: str):
        queue = self._chat_queue()
        if queue and queue[0] == text:
            queue.pop(0)

    def _run_test_queue_processor(self):
        while True:
            try:
                time.sleep(0.05)
                if self.program.setupTest.getMetaMode() != "test":
                    continue
                if self._is_chat_decides_mode():
                    with self._lock:
                        if self.state.executing_input:
                            continue
                        if self.state.setup_countdown_active or self.state.manual_setup_active:
                            continue
                        text = self._peek_next_test_queue_item()
                        if text and text in GOVERNANCE_VOTE_CHOICES:
                            self.state.executing_input = text
                        else:
                            text = None
                    if text:
                        self._prune_and_recompute_chat_decides(notify=True)
                        with self._lock:
                            self.state.executing_input = ""
                        continue
                if self._effective_government() != "anarchy":
                    continue
                with self._lock:
                    if self.state.executing_input:
                        continue
                    if self.state.setup_countdown_active or self.state.manual_setup_active:
                        continue
                    text = self._peek_next_test_queue_item()
                    if not text:
                        continue
                    self.state.executing_input = text
                self._notify()
                try:
                    self._execute_chat_command(text)
                finally:
                    with self._lock:
                        self.state.executing_input = ""
                        self._remove_test_queue_item(text)
                    self._notify()
            except Exception as error:
                logger.exception("Test queue processor error: %s", error)
                with self._lock:
                    self.state.executing_input = ""
                self._notify()

    def _fake_chat_part(self, pool: List[str]) -> str:
        st = self.program.setupTest
        name = random.choice(pool).lower()
        roll = random.random()
        prefix = ""
        timing_modes = [mode for mode in ("tap", "press", "hold") if st.isTimingModeEnabled(mode)]
        if roll < 0.25 and st.getAllowTimingPrefixes() and timing_modes:
            mode = random.choice(timing_modes)
            prefix = random.choice((mode, mode[0]))
        elif roll < 0.4 and st.getAllowCustomInputDuration():
            durations = [d for d in FAKE_CHAT_DURATIONS if d <= st.getMaxTimeLength()]
            if durations:
                prefix = f"({random.choice(durations):g})"
        suffix = ""
        if name != WAIT_INPUT and st.getAllowInputRepeat() and random.random() < 0.2:
            suffix = str(random.randint(2, 5))
        return f"{prefix}{name}{suffix}"

    def _fake_chat_command(self, pool: List[str]) -> Optional[str]:
        """A line like viewers type, using only the syntax the chat rules allow:
        tap/press/hold prefixes, custom durations, repeats and sequences.

        Every candidate is checked against the current rules; None when no
        allowed line could be made (e.g. every input is disabled).
        """
        st = self.program.setupTest
        for _ in range(5):
            count = 1
            max_length = st.getMaxInputSequenceLength()
            if st.getAllowInputSequences() and max_length > 1 and random.random() < 0.2:
                count = random.randint(2, max_length)
            text = ",".join(self._fake_chat_part(pool) for _ in range(count))
            if self._is_valid_chat_command(text):
                return text
        plain = [name.lower() for name in pool if self._is_valid_chat_command(name.lower())]
        return random.choice(plain) if plain else None

    def _pick_fake_anarchy_input(self, pool: List[str]) -> Optional[str]:
        return self._fake_chat_command(pool)

    def _pick_fake_democracy_input(self, pool: List[str]) -> Optional[str]:
        # Pile onto an existing vote, but only one that the current rules still allow.
        votes = [text for text in self.program.setupTest.getVoteList() if self._is_valid_chat_command(text)]
        if votes and random.random() < 0.65:
            return random.choice(votes)
        return self._fake_chat_command(pool)

    def _roll_fake_chat_input(self, pool: List[str]):
        if self._is_chat_decides_mode():
            text = random.choice(pool).lower()
            if text in GOVERNANCE_VOTE_CHOICES:
                self._enqueue_chat_decides_governance_vote(text)
                return
            pool = [name for name in pool if name not in GOVERNANCE_VOTE_CHOICES]
            if not pool:
                return
        if self._effective_government() == "democracy":
            text = self._pick_fake_democracy_input(pool)
            if text:
                self._enqueue_democracy_vote(text)
            return
        text = self._pick_fake_anarchy_input(pool)
        if text:
            self._append_chat_line(text)

    def _default_execution_seconds(self) -> float:
        mode = self.state.default_time_length or "press"
        if mode == "tap":
            return self.state.tap_time
        if mode == "hold":
            return self.state.hold_time
        return self.state.press_time

    def _fake_chat_roll_interval(self) -> float:
        execution = self._default_execution_seconds()
        # Roll much faster than execution so the chat box fills up.
        return max(0.04, execution * 0.15)

    def _begin_democracy_vote_round(self):
        total = (self.state.democracy_minutes * 60) + self.state.democracy_seconds
        self.program.setupTest.setMetaDemTime(total)
        self.program.setupTest.setLastDemocracyItem(None)
        self.program.setupTest.resetVoteList()
        self._pending_democracy_votes.clear()
        self.state.vote_slots = [VoteSlot() for _ in range(DEMOCRACY_LEADER_SLOTS)]
        self.state.democracy_countdown_label = self._format_democracy_countdown(total)
        self.state.democracy_timer_running = True
        self._schedule_democracy_tick()

    def start_fake_chat_roll(self, count: int = 0):
        if self.state.meta_mode != "test":
            return
        with self._lock:
            if self.state.fake_chat_running:
                return
            self.state.fake_chat_running = True
            if self.state.government in ("democracy", CHAT_DECIDES_MODE) and not self.state.democracy_timer_running:
                if self.state.government == "democracy" or self._effective_government() == "democracy":
                    self._begin_democracy_vote_round()
        self._notify()
        threading.Thread(
            target=self._run_fake_chat_roll,
            args=(count,),
            daemon=True,
        ).start()

    def stop_fake_chat_roll(self):
        with self._lock:
            self.state.fake_chat_running = False
        self._stop_democracy_vote_round()
        self._notify()

    def _run_fake_chat_roll(self, count: int):
        try:
            rolled = 0
            while True:
                with self._lock:
                    if not self.state.fake_chat_running:
                        break
                # Re-read every roll so inputs disabled mid-roll stop appearing.
                pool = self._valid_test_inputs()
                self._roll_fake_chat_input(pool)
                self._notify()
                rolled += 1
                if count > 0 and rolled >= count:
                    break
                time.sleep(self._fake_chat_roll_interval())
        finally:
            with self._lock:
                self.state.fake_chat_running = False
            self._notify()

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
        else:
            self.stop_fake_chat_roll()
            with self._lock:
                self.state.executing_input = ""
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
        if normalized not in ("anarchy", "democracy", CHAT_DECIDES_MODE):
            return
        self.stop_fake_chat_roll()
        self._cancel_chat_decides_prune_timer()
        with self._lock:
            self.program.setupTest.setMetaGov(normalized)
            self.state.government = normalized
            if normalized == CHAT_DECIDES_MODE:
                self._clear_chat_decides_governance_votes()
                self.state.chat_decides_active_gov = self.state.chat_decides_default_gov
                sub_gov = self.state.chat_decides_active_gov
            else:
                sub_gov = normalized
            if self.state.setup_countdown_active or self.state.manual_setup_active:
                if sub_gov == "anarchy":
                    self.program.setupTest.setAnarchyThreadStatus(False)
                    self.program.setupTest.democracyThreadStatus = False
                else:
                    self.program.setupTest.anarchyThreadStatus = False
                    self.program.setupTest.setDemocracyThreadStatus(False)
            else:
                self._apply_sub_government_threads(sub_gov)
        if normalized == CHAT_DECIDES_MODE:
            self._schedule_chat_decides_prune()
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
                self._clear_democracy_chat()
        if self.state.setup_link_mode == "automatic":
            self.scan_emulator()
        else:
            self._refresh_automatic_link_availability()
            self._notify()

    def set_time_lengths(
        self,
        tap: float,
        press: float,
        hold: float,
        default: str,
        timing_tap_enabled: bool = True,
        timing_press_enabled: bool = True,
        timing_hold_enabled: bool = True,
    ):
        enabled = {
            "tap": timing_tap_enabled,
            "press": timing_press_enabled,
            "hold": timing_hold_enabled,
        }
        if sum(enabled.values()) < 1:
            return
        if default not in enabled or not enabled[default]:
            default = next(mode for mode in ("tap", "press", "hold") if enabled[mode])
        with self._lock:
            self.program.setupTest.setTapTime(tap)
            self.program.setupTest.setPressTime(press)
            self.program.setupTest.setHoldTime(hold)
            self.program.setupTest.setTimingTapEnabled(timing_tap_enabled)
            self.program.setupTest.setTimingPressEnabled(timing_press_enabled)
            self.program.setupTest.setTimingHoldEnabled(timing_hold_enabled)
            self.program.setupTest.setDefaultTimeLength(default)
            self.state.tap_time = tap
            self.state.press_time = press
            self.state.hold_time = hold
            self.state.default_time_length = default
            self.state.timing_tap_enabled = timing_tap_enabled
            self.state.timing_press_enabled = timing_press_enabled
            self.state.timing_hold_enabled = timing_hold_enabled
        self._notify()

    def set_chat_input_policy(
        self,
        allow_timing_prefixes: bool,
        allow_input_repeat: bool,
        allow_custom_duration: bool,
        max_duration: int,
        allow_input_sequences: bool,
        max_sequence_length: int,
    ):
        max_duration = max(1, min(int(max_duration), 99))
        max_sequence_length = max(1, min(int(max_sequence_length), 10))
        with self._lock:
            self.program.setupTest.setAllowTimingPrefixes(allow_timing_prefixes)
            self.program.setupTest.setAllowInputRepeat(allow_input_repeat)
            self.program.setupTest.setAllowCustomInputDuration(allow_custom_duration)
            self.program.setupTest.setMaxTimeLength(max_duration)
            self.program.setupTest.setAllowInputSequences(allow_input_sequences)
            self.program.setupTest.setMaxInputSequenceLength(max_sequence_length)
            self.state.allow_timing_prefixes = allow_timing_prefixes
            self.state.allow_input_repeat = allow_input_repeat
            self.state.allow_custom_input_duration = allow_custom_duration
            self.state.max_input_duration = max_duration
            self.state.allow_input_sequences = allow_input_sequences
            self.state.max_input_sequence_length = max_sequence_length
        self._notify()

    def set_countdown(self, seconds: int):
        with self._lock:
            self.program.setupTest.setCountdown(seconds)
            self.state.countdown_seconds = seconds
        self._notify()

    def submit_input(self, text: str):
        text = text.strip().lower().replace(" ", "")
        if not text:
            return

        if text == "clear":
            self.stop_fake_chat_roll()
            with self._lock:
                if self._is_chat_decides_mode():
                    self._clear_chat_decides_governance_votes()
                    self.state.chat_decides_active_gov = self.state.chat_decides_default_gov
                    self.state.anarchy_queue.clear()
                    self._clear_democracy_chat()
                    self.program.setupTest.resetVoteList()
                    self.state.vote_slots = [VoteSlot() for _ in range(DEMOCRACY_LEADER_SLOTS)]
                    self.state.executing_input = ""
                elif self.state.government == "anarchy":
                    self.state.anarchy_queue.clear()
                    self.state.executing_input = ""
                else:
                    self._clear_democracy_chat()
                    self.program.setupTest.resetVoteList()
                    self.state.vote_slots = [VoteSlot() for _ in range(DEMOCRACY_LEADER_SLOTS)]
            self._notify()
            return

        if self._is_chat_decides_mode() and text in GOVERNANCE_VOTE_CHOICES:
            if self.program.setupTest.getMetaMode() == "test":
                self._enqueue_chat_decides_governance_vote(text)
            return

        if not self._is_valid_chat_command(text):
            return

        mode = self.program.setupTest.getMetaMode()
        effective_gov = self._effective_government()

        if mode == "test":
            with self._lock:
                if effective_gov == "anarchy":
                    self._append_chat_line(text)
                else:
                    self._enqueue_democracy_vote(text)
            self._notify()
            return

        self._countdown_runner.start_single(text)

    def submit_chat_message(self, user: str, text: str):
        """Queue a message from the live platform chat.

        Unlike the sandbox, viewers can't run commands such as "clear", and
        nothing is queued outside Test mode or while a setup step is running.
        """
        text = text.strip().lower().replace(" ", "")
        if not text or self.program.setupTest.getMetaMode() != "test":
            return
        with self._lock:
            if self.state.setup_countdown_active or self.state.manual_setup_active:
                return

        if self._is_chat_decides_mode() and text in GOVERNANCE_VOTE_CHOICES:
            self._enqueue_chat_decides_governance_vote(text, user=user)
            return

        if not self._is_valid_chat_command(text):
            return

        with self._lock:
            if self._effective_government() == "anarchy":
                self._append_chat_line(text, user=user)
            else:
                self._enqueue_democracy_vote(text, user=user)
        self._notify()

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
        if self._effective_government() == "anarchy":
            self.program.setupTest.setAnarchyThreadStatus(False)
        else:
            self.program.setupTest.setDemocracyThreadStatus(False)

    def _resume_gov_threads(self):
        if not self.state.manual_setup_active:
            self._apply_sub_government_threads(self._effective_government())

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
                self._clear_democracy_chat()
                self._begin_democracy_vote_round()
            else:
                self._stop_democracy_vote_round()
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
        winner_input = None
        notify = False
        with self._lock:
            if not self.state.democracy_timer_running:
                return

            dem_time = self.program.setupTest.getMetaDemTime()
            if dem_time >= 0:
                self.state.democracy_countdown_label = self._format_democracy_countdown(dem_time)
                self.program.setupTest.reduceDemocracyCount()
                self._schedule_democracy_tick()
                notify = True
            else:
                minutes = self.state.democracy_minutes
                seconds = self.state.democracy_seconds
                total = (minutes * 60) + seconds
                self.program.setupTest.setMetaDemTime(total)
                self.program.setupTest.resetVoteList()
                winner_text = self.state.vote_slots[0].input_text
                if winner_text and winner_text != "empty":
                    winner_input = winner_text
                self._reset_dem_votes(ran_out=True)
                self._clear_democracy_chat()
                self.state.democracy_countdown_label = self._format_democracy_countdown(total)
                self.program.setupTest.setLastDemocracyItem(None)
                self._schedule_democracy_tick()
                notify = True
        if winner_input:
            try:
                winner = InputSequence(winner_input, self.program.setupTest)
                self.program.setupTest.metaCommand(winner)
            except Exception:
                pass
        if notify:
            self._notify()

    def _reset_dem_votes(self, ran_out: bool):
        if ran_out:
            winner = self.state.vote_slots[0].input_text
            self.program.setupTest.setLastDemocracyWinner(winner)
            self.state.latest_winner = winner
        self.state.vote_slots = [VoteSlot() for _ in range(DEMOCRACY_LEADER_SLOTS)]

    def _update_vote_slots_from_list(self):
        vote_list = self.program.setupTest.getVoteList()
        sorted_inputs = sorted(vote_list, key=lambda key: vote_list[key], reverse=True)
        slots = [VoteSlot() for _ in range(DEMOCRACY_LEADER_SLOTS)]
        for index, input_text in enumerate(sorted_inputs[:DEMOCRACY_LEADER_SLOTS]):
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
                if self.program.setupTest.getMetaGov() not in ("anarchy", CHAT_DECIDES_MODE):
                    continue
                if self._effective_government() != "anarchy":
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
                    command = InputSequence(text, self.program.setupTest)
                except ValueError:
                    with self._lock:
                        if self.state.anarchy_queue and self.state.anarchy_queue[0] == text:
                            self.state.anarchy_queue.pop(0)
                        self.program.setupTest.setAnarchyThreadStatus(True)
                    continue
                self.program.setupTest.metaCommand(command)
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
                if not self.program.setupTest.getDemocracyThreadStatus():
                    time.sleep(0.05)
                    continue
                if self.program.setupTest.getMetaGov() not in ("democracy", CHAT_DECIDES_MODE):
                    time.sleep(0.05)
                    continue
                if self._effective_government() != "democracy":
                    time.sleep(0.05)
                    continue
                if not self.state.democracy_timer_running:
                    time.sleep(0.05)
                    continue

                processed_any = False
                while True:
                    with self._lock:
                        if not self._pending_democracy_votes:
                            break
                        _serial, text = self._pending_democracy_votes.popleft()
                        processed_any = True
                    self.program.setupTest.adjustVoteList(text)
                    with self._lock:
                        self._update_vote_slots_from_list()
                if processed_any:
                    self._notify()
                else:
                    time.sleep(0.01)
            except Exception as error:
                logger.exception("Democracy thread error: %s", error)
                time.sleep(0.05)

    def shutdown(self):
        self.cancel_manual_setup()
        self._countdown_runner.cancel()
        self._cancel_democracy_timer()
        self._cancel_chat_decides_prune_timer()
