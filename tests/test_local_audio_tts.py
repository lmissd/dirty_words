"""Tests for local audio TTS provider."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from modules.tts.local_audio_tts import LocalAudioTextToSpeech
from modules.utils.config_loader import AppConfig


class FakeAudioPlayer:
    def __init__(self) -> None:
        self.played: list[Path] = []

    def play(self, audio_path: Path) -> None:
        self.played.append(audio_path)


class LocalAudioTtsTests(unittest.TestCase):
    def test_speak_plays_greeting_audio(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "greeting.wav"
            audio_path.write_bytes(b"RIFF")
            player = FakeAudioPlayer()
            config = AppConfig(
                data={
                    "tts": {"enabled": True},
                    "greeting": {"text": "小朋友你好", "audio_path": str(audio_path)},
                },
                path=Path("config/config.example.yaml"),
            )

            tts = LocalAudioTextToSpeech(config, player)
            result = tts.speak("小朋友你好")

            self.assertEqual(result, audio_path)
            self.assertEqual(player.played, [audio_path])


if __name__ == "__main__":
    unittest.main()
