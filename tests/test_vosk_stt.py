"""Tests for offline Vosk speech-to-text helpers."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from modules.app import _build_speech_to_text
from modules.speech_to_text.vosk_stt import _resample_audio, VoskSpeechToText
from modules.utils.config_loader import AppConfig


class VoskSpeechToTextTests(unittest.TestCase):
    def test_build_speech_to_text_returns_vosk_provider(self) -> None:
        config = AppConfig(
            data={"speech_to_text": {"provider": "vosk", "model_path": "models/vosk-model-small-cn-0.22"}},
            path=Path("config/config.example.yaml"),
        )

        with patch.object(VoskSpeechToText, "_load_model", return_value=object()):
            provider = _build_speech_to_text(config)

        self.assertIsInstance(provider, VoskSpeechToText)

    def test_resample_audio_changes_length_to_target_rate(self) -> None:
        audio = np.linspace(-0.5, 0.5, num=48000, dtype=np.float32)

        resampled = _resample_audio(audio, 48000, 16000)

        self.assertEqual(len(resampled), 16000)
        self.assertTrue(np.issubdtype(resampled.dtype, np.floating))


if __name__ == "__main__":
    unittest.main()
