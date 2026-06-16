"""Piper neural TTS adapter."""

from __future__ import annotations

import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from modules.tts.base import TextToSpeechProvider
from modules.utils.audio_player import AudioPlayer
from modules.utils.config_loader import AppConfig
from modules.utils.disk import ensure_free_space
from modules.utils.errors import AudioOutputError, ConfigurationError

LOGGER = logging.getLogger(__name__)


class PiperTextToSpeech(TextToSpeechProvider):
    """Generate speech with Piper and play it locally."""

    def __init__(self, config: AppConfig, audio_player: AudioPlayer) -> None:
        self.config = config
        self.audio_player = audio_player

    def speak(self, text: str) -> Path | None:
        """Generate TTS audio with Piper and play it if enabled."""
        if not bool(self.config.get("tts.enabled", True)):
            LOGGER.info("Piper TTS 已禁用，跳过播报。")
            return None

        output_path = self._resolve_output_path(text)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_free_space(output_path.parent)

        cache_enabled = bool(self.config.get("tts.cache_enabled", True))
        if not cache_enabled or not output_path.exists():
            command = self._build_command(text, output_path)
            LOGGER.info("执行 Piper TTS 命令：%s", command)
            try:
                subprocess.run(command, check=True)
            except (OSError, subprocess.CalledProcessError) as exc:
                raise AudioOutputError(f"Piper TTS 生成失败：{exc}") from exc

        if not output_path.exists():
            raise AudioOutputError(f"Piper TTS 未生成音频文件：{output_path}")

        self.audio_player.play(output_path)
        return output_path

    def _resolve_output_path(self, text: str) -> Path:
        greeting_text = str(self.config.get("greeting.text", "小朋友你好"))
        if text == greeting_text:
            return Path(str(self.config.get("greeting.audio_path", "assets/audio/greeting.wav")))

        configured = self.config.get("tts.output_path", None)
        if configured:
            return Path(str(configured))

        output_dir = Path(str(self.config.get("paths.tts_output_dir", "recordings")))
        filename = datetime.now().strftime("piper_tts_%Y%m%d_%H%M%S.wav")
        return output_dir / filename

    def _build_command(self, text: str, output_path: Path) -> list[str]:
        command_template = self.config.get("tts.command", None)
        if command_template is not None:
            return [str(part).format(text=text, output=str(output_path)) for part in list(command_template)]

        binary = str(self.config.get("tts.binary", "piper"))
        if shutil.which(binary) is None:
            raise ConfigurationError(
                f"未找到 Piper 可执行文件：{binary}。请先安装 Piper，或在 tts.binary 中填写完整路径。"
            )

        raw_model_path = str(self.config.get("tts.model_path", "")).strip()
        if not raw_model_path:
            raise ConfigurationError("缺少 tts.model_path，请指向 Piper 的中文语音模型 .onnx 文件。")
        model_path = Path(raw_model_path).expanduser()
        if not model_path.exists():
            raise ConfigurationError(f"Piper 模型文件不存在：{model_path}")

        config_path = self.config.get("tts.model_config_path", None)
        command = [
            binary,
            "--model",
            str(model_path),
            "--output_file",
            str(output_path),
        ]
        if config_path:
            command.extend(["--config", str(Path(str(config_path)).expanduser())])

        speaker = self.config.get("tts.speaker", None)
        if speaker is not None:
            command.extend(["--speaker", str(speaker)])

        length_scale = self.config.get("tts.length_scale", None)
        if length_scale is not None:
            command.extend(["--length_scale", str(length_scale)])

        noise_scale = self.config.get("tts.noise_scale", None)
        if noise_scale is not None:
            command.extend(["--noise_scale", str(noise_scale)])

        noise_w = self.config.get("tts.noise_w", None)
        if noise_w is not None:
            command.extend(["--noise_w", str(noise_w)])

        command.append(text)
        return command
