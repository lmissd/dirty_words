"""Audio playback abstraction."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from modules.utils.config_loader import AppConfig
from modules.utils.errors import AudioOutputError

LOGGER = logging.getLogger(__name__)


class AudioPlayer:
    """Play generated audio using the configured system command."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def play(self, audio_path: Path) -> None:
        """Play a local audio file if playback is enabled."""
        if not bool(self.config.get("playback.enabled", True)):
            LOGGER.info("音频播放已禁用：%s", audio_path)
            return

        command = str(self.config.get("playback.command", "auto"))
        if command == "auto":
            command_args = self._auto_command(audio_path)
            if command_args is None:
                LOGGER.warning("未找到可用播放器，跳过播放：%s", audio_path)
                return
        else:
            command_args = [command, str(audio_path)]

        try:
            subprocess.run(command_args, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise AudioOutputError(f"音频播放失败：{exc}") from exc

    def _auto_command(self, audio_path: Path) -> list[str] | None:
        suffix = audio_path.suffix.lower()
        if suffix == ".wav" and shutil.which("aplay"):
            alsa_device = self.config.get("playback.alsa_device", None)
            if alsa_device:
                return ["aplay", "-D", str(alsa_device), str(audio_path)]
            return ["aplay", str(audio_path)]
        if shutil.which("mpg123"):
            return ["mpg123", "-q", str(audio_path)]
        if shutil.which("ffplay"):
            return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(audio_path)]
        return None
