"""Background reader that feeds a Twitch channel's chat into ChatPlays."""

import logging
import threading
from typing import Callable, Optional

from Twitch_Connection import Twitch

logger = logging.getLogger(__name__)

RETRY_SECONDS = 5


class TwitchChatListener:
    """Reads one channel's chat anonymously (read-only) on a daemon thread.

    Each start() gets its own stop event, so a listener that is still winding
    down after stop() or a channel change never delivers another message.
    """

    def __init__(self, on_message: Callable[[str, str], None]):
        self._on_message = on_message
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None
        self._channel = ""

    def start(self, channel: str) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive() and channel == self._channel:
                return
            self._stop_locked()
            self._channel = channel
            self._stop_event = threading.Event()
            self._thread = threading.Thread(
                target=self._run,
                args=(channel, self._stop_event),
                name=f"twitch-chat-{channel}",
                daemon=True,
            )
            self._thread.start()
        logger.info("Listening to Twitch chat for #%s", channel)

    def stop(self) -> None:
        with self._lock:
            if self._channel:
                logger.info("Stopped listening to Twitch chat for #%s", self._channel)
            self._stop_locked()

    def _stop_locked(self) -> None:
        if self._stop_event:
            self._stop_event.set()
        self._thread = None
        self._stop_event = None
        self._channel = ""

    def _run(self, channel: str, stop_event: threading.Event) -> None:
        twitch = Twitch()
        try:
            while not stop_event.is_set():
                try:
                    if twitch.sock is None:
                        twitch.twitch_connect(channel)
                    messages = twitch.twitch_receive_messages()
                except Exception as error:
                    logger.warning(
                        "Twitch chat for #%s failed (%s); retrying in %ss",
                        channel,
                        error,
                        RETRY_SECONDS,
                    )
                    _close(twitch)
                    stop_event.wait(RETRY_SECONDS)
                    continue

                for message in messages:
                    if stop_event.is_set():
                        break
                    try:
                        self._on_message(_chatter_name(message), message["message"])
                    except Exception:
                        logger.exception("Could not handle Twitch chat message")
        finally:
            _close(twitch)


def _chatter_name(message: dict) -> str:
    # Use the display name only when it's the login with different
    # capitalization; localized names (e.g. CJK) may not render in the pixel font.
    login = message["username"]
    display = message.get("display_name", "")
    return display if display.lower() == login.lower() else login


def _close(twitch: Twitch) -> None:
    if twitch.sock is not None:
        try:
            twitch.sock.close()
        except OSError:
            pass
        twitch.sock = None
