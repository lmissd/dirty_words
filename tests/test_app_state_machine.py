"""Tests for the app state machine using fake modules."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from modules.app import CivilLanguageRobotApp
from modules.models import CivilityAnalysis
from modules.recorder.base import RecordedAudio
from modules.utils.config_loader import AppConfig
from modules.wakeword.base import WakeEvent


class FakeWakeWord:
    def wait_for_wake(self) -> WakeEvent:
        return WakeEvent(wake_word="小文小文")


class FakeRecorder:
    def __init__(self, audio_path: Path) -> None:
        self.audio_path = audio_path
        self.recorded = False

    def record(self) -> RecordedAudio:
        self.recorded = True
        self.audio_path.write_bytes(b"fake wav")
        return RecordedAudio(path=self.audio_path, duration_seconds=1, sample_rate=16000)


class FakeSpeechToText:
    def transcribe(self, audio_path: Path) -> str:
        return "你这样说让我不舒服"


class FakeAnalyzer:
    def analyze(self, text: str) -> CivilityAnalysis:
        return CivilityAnalysis(
            civilized=True,
            score=90,
            reason="表达了感受，没有攻击他人",
            suggestion="可以继续用这种方式表达自己的想法",
        )


class FakeDisplay:
    def __init__(self) -> None:
        self.result_seen = False
        self.errors: list[str] = []

    def show_standby(self, wake_words: list[str]) -> None:
        pass

    def show_status(self, message: str) -> None:
        pass

    def show_result(self, user_text: str, analysis: CivilityAnalysis) -> None:
        self.result_seen = True

    def show_error(self, message: str) -> None:
        self.errors.append(message)


class FakeTts:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


class FakeSpeechActivity:
    def __init__(self, detected: bool) -> None:
        self.detected = detected
        self.calls: list[float] = []

    def wait_for_speech(self, timeout_seconds: float) -> bool:
        self.calls.append(timeout_seconds)
        return self.detected


class AppStateMachineTests(unittest.TestCase):
    def test_run_once_completes_and_deletes_temp_audio(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "recording.wav"
            display = FakeDisplay()
            tts = FakeTts()
            config = AppConfig(
                data={
                    "app": {"cycle_pause_seconds": 0, "max_error_pause_seconds": 0},
                    "privacy": {"keep_recordings": False},
                    "wakeword": {"wake_words": ["小文小文"]},
                },
                path=Path("config/config.example.yaml"),
            )

            app = CivilLanguageRobotApp(
                config=config,
                wakeword=FakeWakeWord(),
                recorder=FakeRecorder(audio_path),
                speech_to_text=FakeSpeechToText(),
                analyzer=FakeAnalyzer(),
                display=display,
                tts=tts,
            )

            app.run_once()

            self.assertTrue(display.result_seen)
            self.assertEqual(display.errors, [])
            self.assertEqual(len(tts.spoken), 1)
            self.assertFalse(audio_path.exists())

    def test_run_once_returns_to_standby_when_no_post_wake_speech(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "recording.wav"
            display = FakeDisplay()
            recorder = FakeRecorder(audio_path)
            tts = FakeTts()
            speech_activity = FakeSpeechActivity(detected=False)
            config = AppConfig(
                data={
                    "app": {"cycle_pause_seconds": 0, "max_error_pause_seconds": 0},
                    "privacy": {"keep_recordings": False},
                    "wakeword": {"wake_words": ["范小团你好"]},
                    "post_wake_speech": {"enabled": True, "timeout_seconds": 30},
                },
                path=Path("config/config.example.yaml"),
            )

            app = CivilLanguageRobotApp(
                config=config,
                wakeword=FakeWakeWord(),
                recorder=recorder,
                speech_to_text=FakeSpeechToText(),
                analyzer=FakeAnalyzer(),
                display=display,
                tts=tts,
                speech_activity=speech_activity,
            )

            app.run_once()

            self.assertFalse(recorder.recorded)
            self.assertFalse(display.result_seen)
            self.assertEqual(tts.spoken, [])
            self.assertEqual(speech_activity.calls, [30.0])


if __name__ == "__main__":
    unittest.main()
