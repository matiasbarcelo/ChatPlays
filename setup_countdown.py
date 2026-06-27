"""Dedicated setup-countdown thread.

All setup countdown timing runs on one worker thread. UI status and controller
commands are delegated back to SetupTestService through locked callbacks so HTTP
handlers and gov threads never race the countdown display.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, TYPE_CHECKING, TYPE_CHECKING

if TYPE_CHECKING:
    from setup_test_service import SetupTestService

logger = logging.getLogger(__name__)


class CountdownMode(str, Enum):
    SINGLE = "single"
    GENERAL = "general"
    MANUAL_STEP = "manual_step"


@dataclass
class CountdownJob:
    mode: CountdownMode
    button: Optional[str] = None


class SetupCountdownRunner:
    """Runs setup countdown sequences on a single background thread."""

    def __init__(self, service: SetupTestService):
        self._service = service
        self._jobs: queue.Queue[Optional[CountdownJob]] = queue.Queue()
        self._cancel = threading.Event()
        self._thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="setup-countdown",
        )
        self._thread.start()

    def cancel(self):
        self._cancel.set()

    def start_single(self, button: str):
        self._enqueue(CountdownJob(CountdownMode.SINGLE, button=button))

    def start_general(self):
        self._enqueue(CountdownJob(CountdownMode.GENERAL))

    def start_manual_step(self, button: str):
        self._enqueue(CountdownJob(CountdownMode.MANUAL_STEP, button=button))

    def _enqueue(self, job: CountdownJob):
        self.cancel()
        self._cancel.clear()
        self._jobs.put(job)

    def _worker(self):
        while True:
            job = self._jobs.get()
            if job is None:
                continue
            try:
                if job.mode == CountdownMode.GENERAL:
                    self._run_general()
                elif job.button:
                    self._run_one_button(
                        job.button,
                        manual_step=job.mode == CountdownMode.MANUAL_STEP,
                        manage_session=job.mode != CountdownMode.GENERAL,
                    )
            except Exception:
                logger.exception("Setup countdown failed for job %s", job)

    def _run_general(self):
        buttons = self._service.countdown_input_names()
        if not buttons:
            return

        self._service.countdown_session_begin(manual=False)
        try:
            for button in buttons:
                if self._cancelled():
                    return
                self._run_one_button(button, manual_step=False, manage_session=False)
        finally:
            if not self._cancelled():
                self._service.countdown_session_end(reset_index=True)

    def _run_one_button(
        self,
        button: str,
        *,
        manual_step: bool,
        manage_session: bool,
    ):
        if manage_session:
            self._service.countdown_session_begin(manual=manual_step)

        try:
            seconds = self._service.countdown_seconds_value()
            for remaining in range(seconds, 0, -1):
                if self._cancelled():
                    return
                self._service.countdown_show_tick(button, remaining)
                time.sleep(1)

            if self._cancelled():
                return

            self._service.countdown_show_tick(button, 0)
            self._service.countdown_fire_input(button)
            self._service.countdown_clear_display()

            if manual_step:
                self._service.countdown_manual_step_complete()
            elif manage_session:
                self._service.countdown_session_end(reset_index=False)
        except Exception:
            if manage_session:
                self._service.countdown_session_end(reset_index=False)
            raise

    def _cancelled(self) -> bool:
        return self._cancel.is_set()
