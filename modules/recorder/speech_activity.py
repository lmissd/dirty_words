"""Simple local speech activity detection."""

from __future__ import annotations

import logging
import queue
import struct
import time

from modules.utils.audio_devices import resolve_input_device
from modules.utils.config_loader import AppConfig
from modules.utils.errors import AudioInputError

LOGGER = logging.getLogger(__name__)


class SpeechActivityDetector:
    """Detect whether microphone input contains speech-like energy."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.sample_rate = int(
            config.get("post_wake_speech.sample_rate", config.get("recording.sample_rate", 16000))
        )
        self.channels = int(config.get("post_wake_speech.channels", config.get("recording.channels", 1)))
        self.device = config.get("post_wake_speech.device", config.get("recording.device", None))
        self.block_seconds = float(config.get("post_wake_speech.block_seconds", 0.25))
        self.threshold = int(config.get("post_wake_speech.rms_threshold", 500))
        self.required_blocks = int(config.get("post_wake_speech.required_blocks", 2))
        self._audio_queue: queue.Queue[bytes] = queue.Queue()

    def wait_for_speech(self, timeout_seconds: float) -> bool:
        """Return True when speech-like audio is detected before timeout."""
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise AudioInputError("缺少 sounddevice 依赖，请先执行 pip install -r requirements.txt") from exc

        block_size = max(1, int(self.sample_rate * self.block_seconds))
        deadline = time.monotonic() + timeout_seconds
        speech_blocks = 0
        device = resolve_input_device(
            self.config,
            "post_wake_speech.device",
            fallback_key="recording.device",
            channels=self.channels,
            sd_module=sd,
        )

        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=block_size,
                device=device,
                dtype="int16",
                channels=self.channels,
                callback=self._audio_callback,
            ):
                while time.monotonic() < deadline:
                    remaining = max(0.0, deadline - time.monotonic())
                    try:
                        data = self._audio_queue.get(timeout=min(self.block_seconds, remaining))
                    except queue.Empty:
                        continue

                    rms = _pcm16_rms(data)
                    LOGGER.debug("唤醒后语音活动 RMS：%s", rms)
                    if rms >= self.threshold:
                        speech_blocks += 1
                        if speech_blocks >= self.required_blocks:
                            LOGGER.info("检测到唤醒后的语音活动，RMS=%s", rms)
                            return True
                    else:
                        speech_blocks = 0
        except Exception as exc:
            raise AudioInputError(f"唤醒后语音活动检测失败，请检查麦克风：{exc}") from exc

        LOGGER.info("唤醒后 %.1f 秒内没有检测到语音活动。", timeout_seconds)
        return False

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            LOGGER.warning("语音活动检测音频输入状态：%s", status)
        self._audio_queue.put(bytes(indata))


def _pcm16_rms(data: bytes) -> int:
    """Calculate RMS for little-endian signed 16-bit PCM bytes."""
    if len(data) < 2:
        return 0

    usable_length = len(data) - (len(data) % 2)
    sample_count = usable_length // 2
    if sample_count == 0:
        return 0

    total = 0
    for (sample,) in struct.iter_unpack("<h", data[:usable_length]):
        total += sample * sample
    return int((total / sample_count) ** 0.5)
