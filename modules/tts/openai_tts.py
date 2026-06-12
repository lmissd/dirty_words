"""OpenAI TTS adapter."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from modules.tts.base import TextToSpeechProvider
from modules.utils.audio_player import AudioPlayer
from modules.utils.config_loader import AppConfig
from modules.utils.disk import ensure_free_space
from modules.utils.errors import ApiError
from modules.utils.openai_client import build_openai_client

LOGGER = logging.getLogger(__name__)


class OpenAITextToSpeech(TextToSpeechProvider):
    """Generate speech with OpenAI TTS and play it locally."""

    def __init__(self, config: AppConfig, audio_player: AudioPlayer) -> None:
        self.config = config
        self.audio_player = audio_player
        self.client = build_openai_client(config)

    def speak(self, text: str) -> Path | None:
        """Generate TTS audio and play it if enabled."""
        if not bool(self.config.get("tts.enabled", True)):
            LOGGER.info("TTS 已禁用，跳过播报。")
            return None

        model = str(self.config.get("tts.model", "gpt-4o-mini-tts"))
        voice = str(self.config.get("tts.voice", "alloy"))
        output_format = str(self.config.get("tts.output_format", "wav"))
        output_dir = Path(str(self.config.get("paths.tts_output_dir", "recordings")))
        ensure_free_space(output_dir)

        filename = datetime.now().strftime(f"tts_%Y%m%d_%H%M%S.{output_format}")
        output_path = output_dir / filename

        try:
            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                response_format=output_format,
            )
            response.write_to_file(str(output_path))
            LOGGER.info("TTS 生成完成：%s", output_path)
            self.audio_player.play(output_path)
            return output_path
        except Exception as exc:
            raise ApiError(f"TTS API 调用失败：{exc}") from exc
