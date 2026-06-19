"""Tests for the app state machine using fake modules."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from modules.app import CivilLanguageRobotApp
from modules.models import CivilityAnalysis
from modules.recorder.base import PcmAudioBuffer, RecordedAudio
from modules.utils.config_loader import AppConfig
from modules.utils.errors import ApiError
from modules.wakeword.base import WakeEvent


class FakeWakeWord:
    def __init__(self) -> None:
        self.calls = 0

    def wait_for_wake(self) -> WakeEvent:
        self.calls += 1
        return WakeEvent(wake_word="小文小文")


class FakeRecorder:
    def __init__(self, audio_path: Path) -> None:
        self.audio_path = audio_path
        self.recorded = False
        self.record_count = 0
        self.pre_roll_audio: PcmAudioBuffer | None = None

    def record(self, pre_roll_audio: PcmAudioBuffer | None = None) -> RecordedAudio:
        self.recorded = True
        self.record_count += 1
        self.pre_roll_audio = pre_roll_audio
        self.audio_path.write_bytes(b"fake wav")
        return RecordedAudio(path=self.audio_path, duration_seconds=1, sample_rate=16000)


class FakeSpeechToText:
    def transcribe(self, audio_path: Path) -> str:
        return "你这样说让我不舒服"


class SequenceSpeechToText:
    def __init__(self, results: list[str | Exception]) -> None:
        self.results = list(results)

    def transcribe(self, audio_path: Path) -> str:
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


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
        self.statuses: list[str] = []
        self.wake_successes: list[str] = []

    def show_standby(self, wake_words: list[str]) -> None:
        pass

    def show_status(self, message: str) -> None:
        self.statuses.append(message)

    def show_wake_success(self, wake_word: str) -> None:
        self.wake_successes.append(wake_word)

    def show_result(self, user_text: str, analysis: CivilityAnalysis) -> None:
        self.result_seen = True

    def show_error(self, message: str) -> None:
        self.errors.append(message)


class FakeTts:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


class FakeGreetingTts(FakeTts):
    pass


class FakeSpeechActivity:
    def __init__(self, detected: bool) -> None:
        self.results = [detected]
        self.calls: list[float] = []

    def wait_for_speech(self, timeout_seconds: float) -> bool:
        self.calls.append(timeout_seconds)
        if self.results:
            return self.results.pop(0)
        return False


class SequenceSpeechActivity(FakeSpeechActivity):
    def __init__(self, results: list[bool]) -> None:
        self.results = list(results)
        self.calls: list[float] = []


class PreRollSpeechActivity(SequenceSpeechActivity):
    def __init__(self, results: list[bool], pre_roll_audio: PcmAudioBuffer) -> None:
        super().__init__(results)
        self._pre_roll_audio = pre_roll_audio
        self.last_pre_roll_audio: PcmAudioBuffer | None = None

    def wait_for_speech(self, timeout_seconds: float) -> bool:
        detected = super().wait_for_speech(timeout_seconds)
        self.last_pre_roll_audio = self._pre_roll_audio if detected else None
        return detected


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
                    "greeting": {"enabled_in_main_flow": False},
                    "analysis": {"remind_only_on_uncivilized": False},
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
                    "greeting": {"enabled_in_main_flow": False},
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

    def test_run_once_skips_reminder_when_text_is_civilized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "recording.wav"
            display = FakeDisplay()
            tts = FakeTts()
            greeting_tts = FakeGreetingTts()
            config = AppConfig(
                data={
                    "app": {"cycle_pause_seconds": 0, "max_error_pause_seconds": 0},
                    "privacy": {"keep_recordings": False},
                    "wakeword": {"wake_words": ["饭团饭团"]},
                    "greeting": {"text": "小朋友你好", "enabled_in_main_flow": True},
                    "analysis": {"remind_only_on_uncivilized": True},
                    "post_wake_speech": {"enabled": False},
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
                greeting_tts=greeting_tts,
            )

            app.run_once()

            self.assertEqual(greeting_tts.spoken, ["小朋友你好"])
            self.assertEqual(tts.spoken, [])
            self.assertFalse(display.result_seen)
            self.assertIn("这次表达很文明，继续保持。", display.statuses)

    def test_run_once_plays_wake_greeting_before_followup_listen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "recording.wav"
            display = FakeDisplay()
            tts = FakeTts()
            greeting_tts = FakeGreetingTts()
            speech_activity = FakeSpeechActivity(detected=False)
            config = AppConfig(
                data={
                    "app": {"cycle_pause_seconds": 0, "max_error_pause_seconds": 0},
                    "privacy": {"keep_recordings": False},
                    "wakeword": {"wake_words": ["饭团饭团"]},
                    "greeting": {"text": "小朋友你好", "enabled_in_main_flow": True},
                    "post_wake_speech": {"enabled": True, "timeout_seconds": 30},
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
                speech_activity=speech_activity,
                greeting_tts=greeting_tts,
            )

            app.run_once()

            self.assertEqual(greeting_tts.spoken, ["小朋友你好"])
            self.assertEqual(display.wake_successes, ["小文小文"])
            self.assertEqual(speech_activity.calls, [30.0])
            self.assertFalse(display.result_seen)

    def test_continuous_session_refreshes_idle_timeout_after_each_detected_speech(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "recording.wav"
            display = FakeDisplay()
            recorder = FakeRecorder(audio_path)
            wakeword = FakeWakeWord()
            tts = FakeTts()
            greeting_tts = FakeGreetingTts()
            speech_activity = SequenceSpeechActivity([True, True, False])
            config = AppConfig(
                data={
                    "app": {"cycle_pause_seconds": 0, "max_error_pause_seconds": 0},
                    "privacy": {"keep_recordings": False},
                    "wakeword": {"wake_words": ["饭团饭团"]},
                    "greeting": {"text": "小朋友你好", "enabled_in_main_flow": True},
                    "analysis": {"remind_only_on_uncivilized": False},
                    "post_wake_speech": {
                        "enabled": True,
                        "timeout_seconds": 30,
                        "continuous_session": True,
                    },
                },
                path=Path("config/config.example.yaml"),
            )

            app = CivilLanguageRobotApp(
                config=config,
                wakeword=wakeword,
                recorder=recorder,
                speech_to_text=FakeSpeechToText(),
                analyzer=FakeAnalyzer(),
                display=display,
                tts=tts,
                speech_activity=speech_activity,
                greeting_tts=greeting_tts,
            )

            app.run_once()

            self.assertEqual(wakeword.calls, 1)
            self.assertEqual(recorder.record_count, 2)
            self.assertEqual(len(tts.spoken), 2)
            # Each detected utterance starts a new full idle timeout instead of returning to wake-word mode.
            self.assertEqual(speech_activity.calls, [30.0, 30.0, 30.0])
            self.assertEqual(greeting_tts.spoken, ["小朋友你好"])

    def test_continuous_session_passes_pre_roll_audio_to_recorder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "recording.wav"
            display = FakeDisplay()
            recorder = FakeRecorder(audio_path)
            pre_roll_audio = PcmAudioBuffer(data=b"\x01\x00\x02\x00", sample_rate=16000, channels=1)
            speech_activity = PreRollSpeechActivity([True, False], pre_roll_audio)
            config = AppConfig(
                data={
                    "app": {"cycle_pause_seconds": 0, "max_error_pause_seconds": 0},
                    "privacy": {"keep_recordings": False},
                    "wakeword": {"wake_words": ["饭团饭团"]},
                    "greeting": {"enabled_in_main_flow": False},
                    "analysis": {"remind_only_on_uncivilized": False},
                    "post_wake_speech": {
                        "enabled": True,
                        "timeout_seconds": 30,
                        "continuous_session": True,
                    },
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
                tts=FakeTts(),
                speech_activity=speech_activity,
            )

            app.run_once()

            self.assertEqual(recorder.pre_roll_audio, pre_roll_audio)

    def test_continuous_session_keeps_listening_after_one_utterance_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "recording.wav"
            display = FakeDisplay()
            recorder = FakeRecorder(audio_path)
            wakeword = FakeWakeWord()
            tts = FakeTts()
            speech_activity = SequenceSpeechActivity([True, True, False])
            config = AppConfig(
                data={
                    "app": {"cycle_pause_seconds": 0, "max_error_pause_seconds": 0},
                    "privacy": {"keep_recordings": False},
                    "wakeword": {"wake_words": ["饭团饭团"]},
                    "greeting": {"enabled_in_main_flow": False},
                    "analysis": {"remind_only_on_uncivilized": False},
                    "post_wake_speech": {
                        "enabled": True,
                        "timeout_seconds": 30,
                        "continuous_session": True,
                        "error_pause_seconds": 0,
                    },
                },
                path=Path("config/config.example.yaml"),
            )

            app = CivilLanguageRobotApp(
                config=config,
                wakeword=wakeword,
                recorder=recorder,
                speech_to_text=SequenceSpeechToText(
                    [ApiError("本地语音识别未识别到有效文本。"), "我很喜欢你"]
                ),
                analyzer=FakeAnalyzer(),
                display=display,
                tts=tts,
                speech_activity=speech_activity,
            )

            app.run_once()

            self.assertEqual(wakeword.calls, 1)
            self.assertEqual(recorder.record_count, 2)
            self.assertEqual(len(tts.spoken), 1)
            self.assertEqual(speech_activity.calls, [30.0, 30.0, 30.0])
            self.assertIn("这句话没有听清或处理失败，请再说一遍。", display.statuses)


if __name__ == "__main__":
    unittest.main()
