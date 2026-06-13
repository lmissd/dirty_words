"""Tests for local audio playback device selection."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from modules.utils.audio_player import AudioPlayer
from modules.utils.config_loader import AppConfig


class AudioPlayerTests(unittest.TestCase):
    def test_auto_playback_selects_output_device(self) -> None:
        config = AppConfig(
            data={"playback": {"alsa_device": "auto", "prefer_pipewire": False}},
            path=Path("config/config.example.yaml"),
        )
        fake_sounddevice = SimpleNamespace(
            default=SimpleNamespace(device=[1, 0]),
            query_devices=lambda: [
                {"name": "USB Audio Device: - (hw:3,0)", "max_input_channels": 1, "max_output_channels": 0},
                {"name": "bcm2835 Headphones: - (hw:2,0)", "max_input_channels": 0, "max_output_channels": 8},
            ],
        )

        with patch("modules.utils.audio_player.shutil.which", return_value="/usr/bin/aplay"):
            with patch.dict("sys.modules", {"sounddevice": fake_sounddevice}):
                command = AudioPlayer(config)._auto_command(Path("greeting.wav"))

        self.assertEqual(command, ["aplay", "-D", "plughw:2,0", "greeting.wav"])

    def test_auto_playback_prefers_pipewire_default_sink(self) -> None:
        config = AppConfig(
            data={"playback": {"alsa_device": "auto", "prefer_pipewire": True}},
            path=Path("config/config.example.yaml"),
        )

        def fake_which(command: str) -> str | None:
            return f"/usr/bin/{command}" if command in {"aplay", "pw-play"} else None

        with patch("modules.utils.audio_player.shutil.which", side_effect=fake_which):
            command = AudioPlayer(config)._auto_command(Path("greeting.wav"))

        self.assertEqual(command, ["pw-play", "greeting.wav"])

    def test_explicit_alsa_device_is_respected(self) -> None:
        config = AppConfig(
            data={"playback": {"alsa_device": "plughw:3,0"}},
            path=Path("config/config.example.yaml"),
        )

        with patch("modules.utils.audio_player.shutil.which", return_value="/usr/bin/aplay"):
            command = AudioPlayer(config)._auto_command(Path("greeting.wav"))

        self.assertEqual(command, ["aplay", "-D", "plughw:3,0", "greeting.wav"])


if __name__ == "__main__":
    unittest.main()
