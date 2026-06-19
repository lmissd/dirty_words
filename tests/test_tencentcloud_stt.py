"""Tests for Tencent Cloud speech-to-text helpers."""

from __future__ import annotations

import io
import os
import wave
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from modules.app import _build_speech_to_text
from modules.speech_to_text.tencentcloud_stt import TencentCloudSpeechToText, _build_tencent_wav_bytes
from modules.utils.config_loader import AppConfig


class TencentCloudSpeechToTextTests(unittest.TestCase):
    def test_build_speech_to_text_returns_tencentcloud_provider(self) -> None:
        config = AppConfig(
            data={
                "speech_to_text": {"provider": "tencentcloud", "sample_rate": 16000},
                "tencentcloud": {
                    "secret_id_env": "TEST_TENCENT_SECRET_ID",
                    "secret_key_env": "TEST_TENCENT_SECRET_KEY",
                },
            },
            path=Path("config/config.example.yaml"),
        )
        os.environ["TEST_TENCENT_SECRET_ID"] = "secret-id"
        os.environ["TEST_TENCENT_SECRET_KEY"] = "secret-key"
        try:
            provider = _build_speech_to_text(config)
        finally:
            os.environ.pop("TEST_TENCENT_SECRET_ID", None)
            os.environ.pop("TEST_TENCENT_SECRET_KEY", None)

        self.assertIsInstance(provider, TencentCloudSpeechToText)

    def test_build_tencent_wav_bytes_returns_wav_container(self) -> None:
        fake_pcm16 = np.array([0, 1024, -1024, 0] * 4000, dtype=np.int16)
        audio_path = Path("fake.wav")

        with patch("modules.speech_to_text.tencentcloud_stt._load_audio", return_value=fake_pcm16):
            wav_bytes = _build_tencent_wav_bytes(audio_path, 16000)

        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            self.assertEqual(wav_file.getframerate(), 16000)
            self.assertEqual(wav_file.getnchannels(), 1)
            self.assertGreater(wav_file.getnframes(), 0)


if __name__ == "__main__":
    unittest.main()
