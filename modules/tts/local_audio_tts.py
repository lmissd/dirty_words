"""Local audio playback TTS provider."""

from __future__ import annotations

import logging
from pathlib import Path

from modules.tts.base import TextToSpeechProvider
from modules.utils.audio_player import AudioPlayer
from modules.utils.config_loader import AppConfig
from modules.utils.errors import AudioOutputError

LOGGER = logging.getLogger(__name__)


class LocalAudioTextToSpeech(TextToSpeechProvider):
    """Play pre-generated local audio instead of calling a cloud TTS API."""

    def __init__(self, config: AppConfig, audio_player: AudioPlayer) -> None:
        self.config = config
        self.audio_player = audio_player

    def speak(self, text: str) -> Path | None:
        """Play a configured local audio file for the requested text."""
        if not bool(self.config.get("tts.enabled", True)):
            LOGGER.info("本地 TTS 已禁用，跳过播报。")
            return None

        audio_path = self._resolve_audio_path(text)
        if not audio_path.exists():
            raise AudioOutputError(
                f"本地问候音频不存在：{audio_path}。请先生成或放置该 wav 文件。"
            )

        LOGGER.info("播放本地音频：%s -> %s", text, audio_path)
        self.audio_player.play(audio_path)
        return audio_path

    def _resolve_audio_path(self, text: str) -> Path:
        greeting_text = str(self.config.get("greeting.text", "小朋友你好"))
        if text == greeting_text:
            return Path(str(self.config.get("greeting.audio_path", "assets/audio/greeting.wav")))
        return Path(str(self.config.get("tts.fallback_audio_path", "assets/audio/greeting.wav")))
