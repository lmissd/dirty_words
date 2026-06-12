"""Local command based TTS provider."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from modules.tts.base import TextToSpeechProvider
from modules.utils.audio_player import AudioPlayer
from modules.utils.config_loader import AppConfig
from modules.utils.errors import AudioOutputError

LOGGER = logging.getLogger(__name__)


class LocalCommandTextToSpeech(TextToSpeechProvider):
    """Generate speech with an offline system command, then play it."""

    def __init__(self, config: AppConfig, audio_player: AudioPlayer) -> None:
        self.config = config
        self.audio_player = audio_player

    def speak(self, text: str) -> Path | None:
        """Generate and play local TTS audio."""
        if not bool(self.config.get("tts.enabled", True)):
            LOGGER.info("本地命令 TTS 已禁用，跳过播报。")
            return None

        output_path = self._resolve_output_path(text)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cache_enabled = bool(self.config.get("tts.cache_enabled", True))
        if not cache_enabled or not output_path.exists():
            command = self._build_command(text, output_path)
            LOGGER.info("执行本地 TTS 命令：%s", command)
            try:
                subprocess.run(command, check=True)
            except (OSError, subprocess.CalledProcessError) as exc:
                raise AudioOutputError(f"本地 TTS 生成失败：{exc}") from exc

        if not output_path.exists():
            raise AudioOutputError(f"本地 TTS 未生成音频文件：{output_path}")

        self.audio_player.play(output_path)
        return output_path

    def _resolve_output_path(self, text: str) -> Path:
        greeting_text = str(self.config.get("greeting.text", "小朋友你好"))
        if text == greeting_text:
            return Path(str(self.config.get("greeting.audio_path", "assets/audio/greeting.wav")))
        return Path(str(self.config.get("tts.output_path", "recordings/local_tts.wav")))

    def _build_command(self, text: str, output_path: Path) -> list[str]:
        command_template = self.config.get("tts.command", None)
        if command_template is None:
            command_template = [
                "espeak-ng",
                "-v",
                str(self.config.get("tts.voice", "cmn")),
                "-s",
                str(self.config.get("tts.speed", 150)),
                "-w",
                "{output}",
                "{text}",
            ]

        if isinstance(command_template, str):
            command_parts: list[Any] = command_template.split()
        else:
            command_parts = list(command_template)

        return [
            str(part).format(text=text, output=str(output_path))
            for part in command_parts
        ]
