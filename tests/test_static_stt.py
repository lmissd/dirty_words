"""Tests for static STT provider."""

from __future__ import annotations

import unittest
from pathlib import Path

from modules.speech_to_text.static_stt import StaticSpeechToText
from modules.utils.config_loader import AppConfig


class StaticSpeechToTextTests(unittest.TestCase):
    def test_transcribe_returns_configured_text(self) -> None:
        config = AppConfig(
            data={"speech_to_text": {"static_text": "测试文本"}},
            path=Path("config/config.example.yaml"),
        )

        self.assertEqual(StaticSpeechToText(config).transcribe(Path("x.wav")), "测试文本")


if __name__ == "__main__":
    unittest.main()
