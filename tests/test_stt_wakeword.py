"""Tests for STT wake-word detection behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from modules.utils.config_loader import AppConfig
from modules.utils.errors import ApiError
from modules.wakeword.stt_wakeword import SttWakeWordDetector


class SequenceSpeechToText:
    def __init__(self, results: list[str | Exception]) -> None:
        self.results = list(results)

    def transcribe(self, audio_path: Path) -> str:
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class SttWakeWordDetectorTests(unittest.TestCase):
    def test_wait_for_wake_ignores_empty_transcript_errors_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AppConfig(
                data={
                    "paths": {"audio_temp_dir": temp_dir},
                    "wakeword": {
                        "wake_words": ["饭团饭团"],
                        "wake_aliases": ["饭团"],
                        "display_wake_word": "饭团饭团",
                        "listen_seconds": 0.1,
                        "idle_pause_seconds": 0,
                        "sample_rate": 16000,
                        "channels": 1,
                        "delete_chunks": True,
                        "fuzzy_enabled": True,
                        "fuzzy_threshold": 0.62,
                        "require_greeting": False,
                        "subject_keywords": ["饭团"],
                    },
                },
                path=Path("config/config.example.yaml"),
            )
            detector = SttWakeWordDetector(
                config,
                SequenceSpeechToText([ApiError("腾讯云语音识别返回为空。"), "饭团饭团"]),
            )

            calls = {"count": 0}

            def fake_record_chunk() -> Path:
                calls["count"] += 1
                path = Path(temp_dir) / f"wake_{calls['count']}.wav"
                path.write_bytes(b"fake")
                return path

            detector._record_chunk = fake_record_chunk  # type: ignore[method-assign]

            event = detector.wait_for_wake()

            self.assertEqual(event.wake_word, "饭团饭团")
            self.assertEqual(calls["count"], 2)


if __name__ == "__main__":
    unittest.main()
