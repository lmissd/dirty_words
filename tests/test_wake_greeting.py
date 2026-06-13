"""Tests for wake-greeting mode."""

from __future__ import annotations

import threading
import unittest
from pathlib import Path

from modules.app import WakeGreetingApp, _build_greeting_tts
from modules.tts.local_audio_tts import LocalAudioTextToSpeech
from modules.utils.config_loader import AppConfig
from modules.wakeword.base import WakeEvent


class FakeWakeWord:
    def wait_for_wake(self) -> WakeEvent:
        return WakeEvent(wake_word="范小团你好")


class FakeDisplay:
    def __init__(self) -> None:
        self.statuses: list[str] = []
        self.errors: list[str] = []

    def show_standby(self, wake_words: list[str]) -> None:
        self.statuses.append(",".join(wake_words))

    def show_status(self, message: str) -> None:
        self.statuses.append(message)

    def show_wake_success(self, wake_word: str) -> None:
        self.statuses.append(f"唤醒成功：{wake_word}")

    def show_greeting_complete(self) -> None:
        self.statuses.append("问候完成，返回待机。")

    def show_result(self, user_text, analysis) -> None:
        raise AssertionError("wake-greeting mode must not show analysis results")

    def show_error(self, message: str) -> None:
        self.errors.append(message)


class FakeTts:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


class SignalingTts(FakeTts):
    def __init__(self, started: threading.Event) -> None:
        super().__init__()
        self.started = started

    def speak(self, text: str) -> None:
        self.started.set()
        super().speak(text)


class ConcurrentDisplay(FakeDisplay):
    def __init__(self, tts_started: threading.Event) -> None:
        super().__init__()
        self.tts_started = tts_started
        self.tts_started_during_animation = False

    def show_wake_success(self, wake_word: str) -> None:
        super().show_wake_success(wake_word)
        self.tts_started_during_animation = self.tts_started.wait(timeout=1)


class FakeAudioPlayer:
    def play(self, audio_path: Path) -> None:
        pass


class WakeGreetingTests(unittest.TestCase):
    def test_run_once_greets_without_analysis(self) -> None:
        display = FakeDisplay()
        tts = FakeTts()
        config = AppConfig(
            data={
                "app": {"cycle_pause_seconds": 0, "max_error_pause_seconds": 0},
                "wakeword": {"wake_words": ["范小团你好"]},
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
        self.assertIn("唤醒成功：范小团你好", display.statuses)
        self.assertIn("问候完成，返回待机。", display.statuses)

    def test_greeting_audio_starts_during_wake_animation(self) -> None:
        tts_started = threading.Event()
        display = ConcurrentDisplay(tts_started)
        tts = SignalingTts(tts_started)
        config = AppConfig(
            data={
                "app": {"cycle_pause_seconds": 0, "max_error_pause_seconds": 0},
                "wakeword": {"wake_words": ["范小团你好"]},
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

        self.assertTrue(display.tts_started_during_animation)
        self.assertEqual(tts.spoken, ["小朋友你好"])

    def test_prerecorded_greeting_uses_local_audio_tts(self) -> None:
        config = AppConfig(
            data={"greeting": {"use_prerecorded_audio": True}},
            path=Path("config/config.example.yaml"),
        )

        tts = _build_greeting_tts(config, FakeAudioPlayer())

        self.assertIsInstance(tts, LocalAudioTextToSpeech)


if __name__ == "__main__":
    unittest.main()
