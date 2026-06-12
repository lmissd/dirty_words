"""Tests for wake-greeting mode."""

from __future__ import annotations

import unittest
from pathlib import Path

from modules.app import WakeGreetingApp
from modules.utils.config_loader import AppConfig
from modules.wakeword.base import WakeEvent


class FakeWakeWord:
    def wait_for_wake(self) -> WakeEvent:
        return WakeEvent(wake_word="范小团")


class FakeDisplay:
    def __init__(self) -> None:
        self.statuses: list[str] = []
        self.errors: list[str] = []

    def show_standby(self, wake_words: list[str]) -> None:
        self.statuses.append(",".join(wake_words))

    def show_status(self, message: str) -> None:
        self.statuses.append(message)

    def show_result(self, user_text, analysis) -> None:
        raise AssertionError("wake-greeting mode must not show analysis results")

    def show_error(self, message: str) -> None:
        self.errors.append(message)


class FakeTts:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


class WakeGreetingTests(unittest.TestCase):
    def test_run_once_greets_without_analysis(self) -> None:
        display = FakeDisplay()
        tts = FakeTts()
        config = AppConfig(
            data={
                "app": {"cycle_pause_seconds": 0, "max_error_pause_seconds": 0},
                "wakeword": {"wake_words": ["范小团"]},
                "greeting": {"text": "小朋友你好"},
            },
            path=Path("config/config.example.yaml"),
        )
        app = WakeGreetingApp(
            config=config,
            wakeword=FakeWakeWord(),
            display=display,
            tts=tts,
        )

        app.run_once()

        self.assertEqual(tts.spoken, ["小朋友你好"])
        self.assertEqual(display.errors, [])
        self.assertIn("唤醒成功：范小团", display.statuses)


if __name__ == "__main__":
    unittest.main()
