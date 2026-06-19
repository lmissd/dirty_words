"""Console wake word detector for development."""

from __future__ import annotations

import logging
from typing import Callable

from modules.wakeword.base import WakeEvent, WakeWordDetector

LOGGER = logging.getLogger(__name__)


class ConsoleWakeWordDetector(WakeWordDetector):
    """Use keyboard input to simulate wake word detection."""

    def __init__(self, wake_words: list[str], prompt: str) -> None:
        self.wake_words = wake_words
        self.prompt = prompt

    def wait_for_wake(self, on_ready: Callable[[], None] | None = None) -> WakeEvent:
        """Wait until the user types a configured wake word."""
        if on_ready is not None:
            on_ready()
        LOGGER.info("进入唤醒词监听：%s", self.wake_words)
        while True:
            text = input(f"{self.prompt}\n> ").strip()
            for wake_word in self.wake_words:
                if wake_word in text:
                    LOGGER.info("检测到唤醒词：%s", wake_word)
                    return WakeEvent(wake_word=wake_word)
            LOGGER.info("未匹配唤醒词，继续待机。")
