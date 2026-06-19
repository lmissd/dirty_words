"""Tests for Piper TTS provider."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.tts.piper_tts import PiperTextToSpeech
from modules.utils.config_loader import AppConfig


class FakeAudioPlayer:
    def __init__(self) -> None:
        self.played: list[Path] = []

    def play(self, audio_path: Path) -> None:
        self.played.append(audio_path)


class PiperTtsTests(unittest.TestCase):
    def test_speak_generates_and_plays_greeting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "zh_CN-huayan-medium.onnx"
            model_path.write_bytes(b"model")
            audio_path = Path(temp_dir) / "greeting.wav"
            player = FakeAudioPlayer()
            config = AppConfig(
                data={
                    "paths": {"tts_output_dir": temp_dir},
                    "tts": {
                        "enabled": True,
                        "provider": "piper",
                        "binary": "piper",
                        "model_path": str(model_path),
                        "cache_enabled": False,
                        "length_scale": 0.9,
                    },
                    "greeting": {"text": "小朋友你好", "audio_path": str(audio_path)},
                },
                path=Path("config/config.example.yaml"),
            )

            def fake_run(command, check):
                audio_path.write_bytes(b"RIFF")

            tts = PiperTextToSpeech(config, player)
            with patch("modules.tts.piper_tts.shutil.which", return_value="/usr/bin/piper"):
                with patch("modules.tts.piper_tts.subprocess.run", side_effect=fake_run) as run:
                    result = tts.speak("小朋友你好")

            self.assertEqual(result, audio_path)
            self.assertEqual(player.played, [audio_path])
            run.assert_called_once_with(
                [
                    "piper",
                    "-m",
                    str(model_path),
                    "-f",
                    str(audio_path),
                    "--length-scale",
                    "0.9",
                    "--",
                    "小朋友你好。",
                ],
                check=True,
            )

    def test_supports_python_module_binary_and_extra_piper_options(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "zh_CN-huayan-medium.onnx"
            config_path = Path(temp_dir) / "zh_CN-huayan-medium.onnx.json"
            output_path = Path(temp_dir) / "greeting.wav"
            model_path.write_bytes(b"model")
            config_path.write_text("{}", encoding="utf-8")
            player = FakeAudioPlayer()
            config = AppConfig(
                data={
                    "tts": {
                        "enabled": True,
                        "provider": "piper",
                        "binary": ["/home/pi/.venv312/bin/python", "-m", "piper"],
                        "model_path": str(model_path),
                        "model_config_path": str(config_path),
                        "cache_enabled": False,
                        "length_scale": 1.12,
                        "noise_scale": 0.82,
                        "noise_w": 0.95,
                        "sentence_silence": 0.18,
                        "volume": 1.05,
                        "no_normalize": True,
                    },
                    "greeting": {
                        "text": "小朋友你好",
                        "tts_text": "小朋友，你好呀。",
                        "audio_path": str(output_path),
                    },
                },
                path=Path("config/config.example.yaml"),
            )

            def fake_run(command, check):
                output_path.write_bytes(b"RIFF")

            tts = PiperTextToSpeech(config, player)
            with patch.object(PiperTextToSpeech, "_binary_exists", return_value=True):
                with patch("modules.tts.piper_tts.subprocess.run", side_effect=fake_run) as run:
                    result = tts.speak("小朋友你好")

            self.assertEqual(result, output_path)
            self.assertEqual(player.played, [output_path])
            run.assert_called_once_with(
                [
                    "/home/pi/.venv312/bin/python",
                    "-m",
                    "piper",
                    "-m",
                    str(model_path),
                    "-f",
                    str(output_path),
                    "-c",
                    str(config_path),
                    "--length-scale",
                    "1.12",
                    "--noise-scale",
                    "0.82",
                    "--noise-w-scale",
                    "0.95",
                    "--sentence-silence",
                    "0.18",
                    "--volume",
                    "1.05",
                    "--no-normalize",
                    "--",
                    "小朋友，你好呀。",
                ],
                check=True,
            )

    def test_prepare_text_adds_reading_punctuation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "zh_CN-huayan-medium.onnx"
            model_path.write_bytes(b"model")
            audio_path = Path(temp_dir) / "tts.wav"
            player = FakeAudioPlayer()
            config = AppConfig(
                data={
                    "tts": {
                        "enabled": True,
                        "provider": "piper",
                        "binary": "piper",
                        "model_path": str(model_path),
                        "cache_enabled": False,
                        "output_path": str(audio_path),
                    },
                    "greeting": {"text": "小朋友你好", "audio_path": str(Path(temp_dir) / "greeting.wav")},
                },
                path=Path("config/config.example.yaml"),
            )

            def fake_run(command, check):
                audio_path.write_bytes(b"RIFF")

            tts = PiperTextToSpeech(config, player)
            with patch("modules.tts.piper_tts.shutil.which", return_value="/usr/bin/piper"):
                with patch("modules.tts.piper_tts.subprocess.run", side_effect=fake_run) as run:
                    tts.speak("检测完成\n请换一种更温和的说法")

            run.assert_called_once_with(
                [
                    "piper",
                    "-m",
                    str(model_path),
                    "-f",
                    str(audio_path),
                    "--",
                    "检测完成。请换一种更温和的说法。",
                ],
                check=True,
            )

    def test_uses_custom_command_template_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "custom.wav"
            player = FakeAudioPlayer()
            config = AppConfig(
                data={
                    "tts": {
                        "enabled": True,
                        "provider": "piper",
                        "cache_enabled": False,
                        "command": ["custom-piper", "--out", "{output}", "--text", "{text}"],
                        "output_path": str(output_path),
                    },
                    "greeting": {"text": "小朋友你好", "audio_path": str(Path(temp_dir) / "greeting.wav")},
                },
                path=Path("config/config.example.yaml"),
            )

            def fake_run(command, check):
                output_path.write_bytes(b"RIFF")

            tts = PiperTextToSpeech(config, player)
            with patch("modules.tts.piper_tts.subprocess.run", side_effect=fake_run) as run:
                result = tts.speak("检测完成。存在侮辱性表达。建议：请礼貌一点。")

            self.assertEqual(result, output_path)
            self.assertEqual(player.played, [output_path])
            run.assert_called_once_with(
                [
                    "custom-piper",
                    "--out",
                    str(output_path),
                    "--text",
                    "检测完成。存在侮辱性表达。建议：请礼貌一点。",
                ],
                check=True,
            )

    def test_fixed_output_path_regenerates_dynamic_text_even_when_cache_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "zh_CN-huayan-medium.onnx"
            output_path = Path(temp_dir) / "piper_tts.wav"
            model_path.write_bytes(b"model")
            player = FakeAudioPlayer()
            config = AppConfig(
                data={
                    "tts": {
                        "enabled": True,
                        "provider": "piper",
                        "binary": "piper",
                        "model_path": str(model_path),
                        "cache_enabled": True,
                        "output_path": str(output_path),
                    },
                    "greeting": {"text": "小朋友你好", "audio_path": str(Path(temp_dir) / "greeting.wav")},
                },
                path=Path("config/config.example.yaml"),
            )

            def fake_run(command, check):
                output_path.write_bytes(b"RIFF")

            tts = PiperTextToSpeech(config, player)
            with patch("modules.tts.piper_tts.shutil.which", return_value="/usr/bin/piper"):
                with patch("modules.tts.piper_tts.subprocess.run", side_effect=fake_run) as run:
                    tts.speak("我来提醒一下。存在攻击性表达。")
                    tts.speak("我来提醒一下。语气不够礼貌。")

            self.assertEqual(run.call_count, 2)
            self.assertEqual(player.played, [output_path, output_path])


if __name__ == "__main__":
    unittest.main()
