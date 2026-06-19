"""Piper neural TTS adapter."""

from __future__ import annotations

import logging
import re
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
_DEFAULT_GREETING_TEXT = "小朋友你好"
_TERMINAL_PUNCTUATION = "。！？!?，,；;：:… "


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
        spoken_text = self._prepare_text(text)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_free_space(output_path.parent)

        cache_enabled = bool(self.config.get("tts.cache_enabled", True))
        if not cache_enabled or not output_path.exists() or self._must_regenerate_dynamic_text(text):
            command = self._build_command(spoken_text, output_path)
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
        greeting_text = str(self.config.get("greeting.text", _DEFAULT_GREETING_TEXT))
        if text == greeting_text:
            return Path(str(self.config.get("greeting.audio_path", "assets/audio/greeting.wav")))

        configured = self.config.get("tts.output_path", None)
        if configured:
            return Path(str(configured))

        output_dir = Path(str(self.config.get("paths.tts_output_dir", "recordings")))
        filename = datetime.now().strftime("piper_tts_%Y%m%d_%H%M%S.wav")
        return output_dir / filename

    def _must_regenerate_dynamic_text(self, text: str) -> bool:
        """Avoid replaying stale cached audio when a fixed output path is used for dynamic text."""
        greeting_text = str(self.config.get("greeting.text", _DEFAULT_GREETING_TEXT))
        return text != greeting_text and self.config.get("tts.output_path", None) is not None

    def _prepare_text(self, text: str) -> str:
        greeting_text = str(self.config.get("greeting.text", _DEFAULT_GREETING_TEXT))
        if text == greeting_text:
            text = str(self.config.get("greeting.tts_text", text))

        normalized = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()
        normalized = re.sub(r"\n+", "。", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        if normalized and normalized[-1] not in _TERMINAL_PUNCTUATION:
            normalized = f"{normalized}。"

        return normalized

    def _build_command(self, text: str, output_path: Path) -> list[str]:
        command_template = self.config.get("tts.command", None)
        if command_template is not None:
            return [str(part).format(text=text, output=str(output_path)) for part in list(command_template)]

        binary_command = self._resolve_binary_command()
        if not binary_command:
            raise ConfigurationError(
                "缺少 tts.binary 配置。请填写 Piper 可执行文件，或用列表形式配置 python -m piper。"
            )

        raw_model_path = str(self.config.get("tts.model_path", "")).strip()
        if not raw_model_path:
            raise ConfigurationError("缺少 tts.model_path，请指向 Piper 的中文语音模型 .onnx 文件。")
        model_path = Path(raw_model_path).expanduser()
        if not model_path.exists():
            raise ConfigurationError(f"Piper 模型文件不存在：{model_path}")

        config_path = self.config.get("tts.model_config_path", None)
        command = [
            *binary_command,
            "-m",
            str(model_path),
            "-f",
            str(output_path),
        ]
        if config_path:
            resolved_config_path = Path(str(config_path)).expanduser()
            if resolved_config_path.exists():
                LOGGER.info("检测到 Piper 模型配置文件：%s", resolved_config_path)
                command.extend(["-c", str(resolved_config_path)])
            else:
                LOGGER.warning(
                    "配置中的 Piper 模型配置文件不存在：%s，将让 Piper 自动推断。",
                    resolved_config_path,
                )

        speaker = self.config.get("tts.speaker", None)
        if speaker is not None:
            command.extend(["--speaker", str(speaker)])

        length_scale = self.config.get("tts.length_scale", None)
        if length_scale is not None:
            command.extend(["--length-scale", str(length_scale)])

        noise_scale = self.config.get("tts.noise_scale", None)
        if noise_scale is not None:
            command.extend(["--noise-scale", str(noise_scale)])

        noise_w = self.config.get("tts.noise_w", None)
        if noise_w is not None:
            command.extend(["--noise-w-scale", str(noise_w)])

        sentence_silence = self.config.get("tts.sentence_silence", None)
        if sentence_silence is not None:
            command.extend(["--sentence-silence", str(sentence_silence)])

        volume = self.config.get("tts.volume", None)
        if volume is not None:
            command.extend(["--volume", str(volume)])

        if bool(self.config.get("tts.no_normalize", False)):
            command.append("--no-normalize")

        command.extend(["--", text])
        return command

    def _resolve_binary_command(self) -> list[str]:
        raw_binary = self.config.get("tts.binary", "piper")
        if isinstance(raw_binary, str):
            command = [raw_binary.strip()]
        else:
            command = [str(part).strip() for part in list(raw_binary) if str(part).strip()]

        if not command:
            return []

        binary = command[0]
        if not self._binary_exists(binary):
            raise ConfigurationError(
                f"未找到 Piper 可执行文件：{' '.join(command)}。请先安装 Piper，或在 tts.binary 中填写完整路径。"
            )

        return command

    @staticmethod
    def _binary_exists(binary: str) -> bool:
        binary_path = Path(binary).expanduser()
        if binary_path.exists():
            return True
        return shutil.which(binary) is not None
