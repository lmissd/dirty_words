"""Helpers for selecting stable audio input devices."""

from __future__ import annotations

import logging
from typing import Any

from modules.utils.config_loader import AppConfig
from modules.utils.errors import AudioInputError

LOGGER = logging.getLogger(__name__)

_MISSING = object()
_AUTO_VALUES = {"", "auto", "automatic", "default_auto", "usb"}
_DEFAULT_INPUT_KEYWORDS = ("usb", "microphone", "mic", "audio", "composite", "jieli")


def resolve_input_device(
    config: AppConfig,
    device_key: str,
    *,
    fallback_key: str | None = None,
    channels: int = 1,
    sd_module: Any | None = None,
) -> int | str | None:
    """Resolve a configured microphone device to a stable sounddevice selector."""
    configured = config.get(device_key, _MISSING)
    if configured is _MISSING and fallback_key is not None:
        configured = config.get(fallback_key, _MISSING)
    if configured is _MISSING:
        configured = config.get("audio.input_device", "auto")

    if not _is_auto_device(configured):
        return _validate_configured_device(configured, channels=channels, sd_module=sd_module)

    sd = _load_sounddevice(sd_module)
    devices = list(sd.query_devices())
    candidates = _input_candidates(devices, channels)
    if not candidates:
        raise AudioInputError(_build_no_input_device_message(devices, channels))

    keywords = _input_keywords(config)
    for keyword in keywords:
        preferred = [
            candidate
            for candidate in candidates
            if keyword in str(candidate[1].get("name", "")).lower()
        ]
        if preferred:
            return _log_selected_device(preferred[0], reason=f"匹配关键词 {keyword}")

    default_input = _default_input_index(sd)
    for candidate in candidates:
        if candidate[0] == default_input:
            return _log_selected_device(candidate, reason="使用系统默认输入设备")

    return _log_selected_device(candidates[0], reason="使用第一个可用输入设备")


def _load_sounddevice(sd_module: Any | None) -> Any:
    if sd_module is not None:
        return sd_module

    try:
        import sounddevice as sd
    except ImportError as exc:
        raise AudioInputError("缺少 sounddevice 依赖，请先执行 pip install -r requirements.txt") from exc
    return sd


def _is_auto_device(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in _AUTO_VALUES
    return False


def _validate_configured_device(value: Any, *, channels: int, sd_module: Any | None) -> int | str:
    sd = _load_sounddevice(sd_module)
    device = _coerce_device_value(value)

    try:
        info = sd.query_devices(device, kind="input")
    except TypeError:
        info = sd.query_devices(device)
    except Exception as exc:
        devices = list(sd.query_devices())
        raise AudioInputError(
            f"配置的麦克风设备不可用：{value}。当前设备：{_format_input_devices(devices)}"
        ) from exc

    if int(info.get("max_input_channels", 0)) < channels:
        devices = list(sd.query_devices())
        raise AudioInputError(
            f"配置的麦克风设备输入通道不足：{value}，需要 {channels} 个输入通道。"
            f"当前设备：{_format_input_devices(devices)}"
        )
    return device


def _coerce_device_value(value: Any) -> int | str:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
        return stripped
    return value


def _input_keywords(config: AppConfig) -> tuple[str, ...]:
    configured = config.get("audio.input_device_keywords", _DEFAULT_INPUT_KEYWORDS)
    if not isinstance(configured, list):
        configured = list(_DEFAULT_INPUT_KEYWORDS)
    keywords = tuple(str(item).strip().lower() for item in configured if str(item).strip())
    return keywords or _DEFAULT_INPUT_KEYWORDS


def _input_candidates(devices: list[dict[str, Any]], channels: int) -> list[tuple[int, dict[str, Any]]]:
    return [
        (index, info)
        for index, info in enumerate(devices)
        if int(info.get("max_input_channels", 0)) >= channels
    ]


def _build_no_input_device_message(devices: list[dict[str, Any]], channels: int) -> str:
    formatted_devices = _format_input_devices(devices)
    if devices and all(int(info.get("max_input_channels", 0)) <= 0 for info in devices):
        return (
            f"没有找到支持 {channels} 个输入通道的麦克风设备。"
            f"当前只识别到输出设备：{formatted_devices}。"
            "这通常不是录音脚本本身的问题，而是树莓派当前没有识别到 USB 麦克风输入。"
            "请先执行 `fuser -v /dev/snd/*`、`arecord -l`，"
            "如果仍然没有 USB 录音设备，再重新插拔麦克风或重启后重试。"
        )
    return f"没有找到支持 {channels} 个输入通道的麦克风设备。当前设备：{formatted_devices}"


def _default_input_index(sd: Any) -> int | None:
    default = getattr(sd, "default", None)
    device = getattr(default, "device", None)
    if isinstance(device, (list, tuple)) and device:
        try:
            index = int(device[0])
        except (TypeError, ValueError):
            return None
        return index if index >= 0 else None
    return None


def _log_selected_device(candidate: tuple[int, dict[str, Any]], *, reason: str) -> int:
    index, info = candidate
    LOGGER.info(
        "自动选择麦克风设备：index=%s name=%s max_input_channels=%s reason=%s",
        index,
        info.get("name", ""),
        info.get("max_input_channels", 0),
        reason,
    )
    return index


def _format_input_devices(devices: list[dict[str, Any]]) -> str:
    if not devices:
        return "无音频设备"
    parts = []
    for index, info in enumerate(devices):
        parts.append(
            f"{index}:{info.get('name', '')}"
            f"({info.get('max_input_channels', 0)} in/{info.get('max_output_channels', 0)} out)"
        )
    return "; ".join(parts)
