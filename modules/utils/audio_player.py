"""Audio playback abstraction."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from modules.utils.config_loader import AppConfig
from modules.utils.errors import AudioOutputError

LOGGER = logging.getLogger(__name__)

_AUTO_VALUES = {"", "auto", "automatic", "default_auto"}
_DEFAULT_OUTPUT_KEYWORDS = ("usb", "speaker", "headphone", "audio", "hdmi", "vc4")


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
            if alsa_device and not _is_auto_device(alsa_device):
                return ["aplay", "-D", str(alsa_device), str(audio_path)]
            if bool(self.config.get("playback.prefer_pipewire", True)) and shutil.which("pw-play"):
                return ["pw-play", str(audio_path)]
            auto_device = self._auto_alsa_output_device()
            if auto_device:
                return ["aplay", "-D", auto_device, str(audio_path)]
            return ["aplay", str(audio_path)]
        if suffix == ".wav" and shutil.which("pw-play"):
            return ["pw-play", str(audio_path)]
        if shutil.which("mpg123"):
            return ["mpg123", "-q", str(audio_path)]
        if shutil.which("ffplay"):
            return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(audio_path)]
        return None

    def _auto_alsa_output_device(self) -> str | None:
        try:
            import sounddevice as sd
        except ImportError:
            return None

        try:
            devices = list(sd.query_devices())
        except Exception as exc:
            LOGGER.warning("查询播放设备失败，改用 aplay 默认设备：%s", exc)
            return None

        candidates = [
            (index, info)
            for index, info in enumerate(devices)
            if int(info.get("max_output_channels", 0)) > 0
        ]
        if not candidates:
            return None

        for keyword in _output_keywords(self.config):
            for candidate in candidates:
                name = str(candidate[1].get("name", ""))
                if keyword in name.lower():
                    device = _alsa_device_from_name(name)
                    if device:
                        return _log_selected_output(candidate, device, reason=f"匹配关键词 {keyword}")

        default_output = _default_output_index(sd)
        for candidate in candidates:
            if candidate[0] == default_output:
                device = _alsa_device_from_name(str(candidate[1].get("name", "")))
                if device:
                    return _log_selected_output(candidate, device, reason="使用系统默认输出设备")

        for candidate in candidates:
            device = _alsa_device_from_name(str(candidate[1].get("name", "")))
            if device:
                return _log_selected_output(candidate, device, reason="使用第一个可用输出设备")

        return None


def _is_auto_device(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in _AUTO_VALUES
    return False


def _output_keywords(config: AppConfig) -> tuple[str, ...]:
    configured = config.get("audio.output_device_keywords", _DEFAULT_OUTPUT_KEYWORDS)
    if not isinstance(configured, list):
        configured = list(_DEFAULT_OUTPUT_KEYWORDS)
    keywords = tuple(str(item).strip().lower() for item in configured if str(item).strip())
    return keywords or _DEFAULT_OUTPUT_KEYWORDS


def _alsa_device_from_name(name: str) -> str | None:
    match = re.search(r"\(hw:(\d+),(\d+)\)", name)
    if match is None:
        return None
    return f"plughw:{match.group(1)},{match.group(2)}"


def _default_output_index(sd: Any) -> int | None:
    default = getattr(sd, "default", None)
    device = getattr(default, "device", None)
    if isinstance(device, (list, tuple)) and len(device) > 1:
        try:
            index = int(device[1])
        except (TypeError, ValueError):
            return None
        return index if index >= 0 else None
    return None


def _log_selected_output(candidate: tuple[int, dict[str, Any]], device: str, *, reason: str) -> str:
    index, info = candidate
    LOGGER.info(
        "自动选择播放设备：index=%s name=%s max_output_channels=%s alsa_device=%s reason=%s",
        index,
        info.get("name", ""),
        info.get("max_output_channels", 0),
        device,
        reason,
    )
    return device
