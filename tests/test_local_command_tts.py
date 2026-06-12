"""Tests for local command TTS provider."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.tts.local_command_tts import LocalCommandTextToSpeech
from modules.utils.config_loader import AppConfig


class FakeAudioPlayer:
    def __init__(self) -> None:
        self.played: list[Path] = []

    def play(self, audio_path: Path) -> None:
        self.played.append(audio_path)


class LocalCommandTtsTests(unittest.TestCase):
    def test_speak_generates_and_plays_greeting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "greeting.wav"
            player = FakeAudioPlayer()
            config = AppConfig(
                data={
                    "tts": {
                        "enabled": True,
                        "provider": "local_command",
                        "cache_enabled": False,
                        "command": ["fake-tts", "-w", "{output}", "{text}"],
                    },
                    "greeting": {"text": "小朋友你好", "audio_path": str(audio_path)},
                },
                path=Path("config/config.example.yaml"),
            )

            def fake_run(command, check):
                audio_path.write_bytes(b"RIFF")

            tts = LocalCommandTextToSpeech(config, player)
            with patch("modules.tts.local_command_tts.subprocess.run", side_effect=fake_run) as run:
                result = tts.speak("小朋友你好")

            self.assertEqual(result, audio_path)
            self.assertEqual(player.played, [audio_path])
            run.assert_called_once_with(["fake-tts", "-w", str(audio_path), "小朋友你好"], check=True)


if __name__ == "__main__":
    unittest.main()
