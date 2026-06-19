"""Tests for Tencent Cloud TTS provider wiring."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from modules.app import _build_tts
from modules.tts.tencentcloud_tts import TencentCloudTextToSpeech
from modules.utils.audio_player import AudioPlayer
from modules.utils.config_loader import AppConfig


class TencentCloudTextToSpeechTests(unittest.TestCase):
    def test_build_tts_returns_tencentcloud_provider(self) -> None:
        config = AppConfig(
            data={
                "tts": {"provider": "tencentcloud"},
                "tencentcloud_tts": {
                    "secret_id_env": "TEST_TENCENT_TTS_SECRET_ID",
                    "secret_key_env": "TEST_TENCENT_TTS_SECRET_KEY",
                },
            },
            path=Path("config/config.example.yaml"),
        )
        os.environ["TEST_TENCENT_TTS_SECRET_ID"] = "secret-id"
        os.environ["TEST_TENCENT_TTS_SECRET_KEY"] = "secret-key"
        try:
            provider = _build_tts(config, AudioPlayer(config))
        finally:
            os.environ.pop("TEST_TENCENT_TTS_SECRET_ID", None)
            os.environ.pop("TEST_TENCENT_TTS_SECRET_KEY", None)

        self.assertIsInstance(provider, TencentCloudTextToSpeech)


if __name__ == "__main__":
    unittest.main()
