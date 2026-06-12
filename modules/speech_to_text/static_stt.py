"""Static speech-to-text provider for offline state-machine testing."""

from __future__ import annotations

import logging
from pathlib import Path

from modules.speech_to_text.base import SpeechToTextProvider
from modules.utils.config_loader import AppConfig

LOGGER = logging.getLogger(__name__)


class StaticSpeechToText(SpeechToTextProvider):
    """Return configured text without calling a cloud STT service."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def transcribe(self, audio_path: Path) -> str:
        """Return a configured transcript for testing."""
        text = str(self.config.get("speech_to_text.static_text", "这是一段离线测试语音"))
        LOGGER.info("使用离线占位 STT：%s -> %s", audio_path, text)
        return text
