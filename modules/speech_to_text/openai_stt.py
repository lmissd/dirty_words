"""OpenAI Speech-to-Text adapter."""

from __future__ import annotations

import logging
from pathlib import Path

from modules.speech_to_text.base import SpeechToTextProvider
from modules.utils.config_loader import AppConfig
from modules.utils.errors import ApiError
from modules.utils.openai_client import build_openai_client

LOGGER = logging.getLogger(__name__)


class OpenAISpeechToText(SpeechToTextProvider):
    """Transcribe audio with OpenAI Speech-to-Text."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = build_openai_client(config)

    def transcribe(self, audio_path: Path) -> str:
        """Send a local audio file to OpenAI and return recognized text."""
        model = str(self.config.get("speech_to_text.model", "gpt-4o-mini-transcribe"))
        language = self.config.get("speech_to_text.language", "zh")

        try:
            with audio_path.open("rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    language=language,
                )
            text = getattr(response, "text", None)
            if not text:
                raise ApiError("语音识别返回为空。")
            LOGGER.info("语音识别完成：%s", text)
            return str(text)
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError(f"语音识别 API 调用失败：{exc}") from exc
