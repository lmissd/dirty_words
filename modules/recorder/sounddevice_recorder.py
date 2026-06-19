"""sounddevice-based WAV recorder."""

from __future__ import annotations

import logging
import math
import queue
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from modules.recorder.base import AudioRecorder, PcmAudioBuffer, RecordedAudio
from modules.utils.audio_devices import resolve_input_device
from modules.utils.config_loader import AppConfig
from modules.utils.disk import ensure_free_space
from modules.utils.errors import AudioInputError

LOGGER = logging.getLogger(__name__)


class SoundDeviceRecorder(AudioRecorder):
    """Record microphone audio to a temporary WAV file."""

    def __init__(self, config: AppConfig, *, sd_module: Any | None = None) -> None:
        self.config = config
        self._sd_module = sd_module
        self._audio_queue: queue.Queue[bytes] = queue.Queue()

    def record(self, pre_roll_audio: PcmAudioBuffer | None = None) -> RecordedAudio:
        """Record a WAV file using the configured microphone."""
        sample_rate = int(self.config.get("recording.sample_rate", 16000))
        channels = int(self.config.get("recording.channels", 1))
        output_dir = Path(str(self.config.get("paths.audio_temp_dir", "recordings")))
        ensure_free_space(output_dir)

        filename = datetime.now().strftime("recording_%Y%m%d_%H%M%S.wav")
        output_path = output_dir / filename
        max_duration = float(
            self.config.get("recording.max_duration_seconds", self.config.get("recording.duration_seconds", 7))
        )
        stop_on_silence = bool(self.config.get("recording.stop_on_silence", pre_roll_audio is not None))

        try:
            sd = self._load_sounddevice()
            import soundfile as sf

            device = resolve_input_device(
                self.config,
                "recording.device",
                channels=channels,
                sd_module=sd,
            )
            if stop_on_silence:
                audio = self._record_until_silence(
                    sd,
                    sample_rate=sample_rate,
                    channels=channels,
                    device=device,
                    max_duration=max_duration,
                    pre_roll_audio=pre_roll_audio,
                )
            else:
                audio = self._record_fixed_duration(
                    sd,
                    sample_rate=sample_rate,
                    channels=channels,
                    device=device,
                    duration=max_duration,
                    pre_roll_audio=pre_roll_audio,
                )
            sf.write(output_path, audio, sample_rate, subtype="PCM_16")
            LOGGER.info("录音完成：%s", output_path)
            actual_duration = len(audio) / float(sample_rate)
            return RecordedAudio(path=output_path, duration_seconds=actual_duration, sample_rate=sample_rate)
        except Exception as exc:
            raise AudioInputError(f"录音失败，请检查麦克风：{exc}") from exc

    def _load_sounddevice(self) -> Any:
        if self._sd_module is not None:
            return self._sd_module
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise AudioInputError("缺少 sounddevice 依赖，请先执行 pip install -r requirements.txt") from exc
        return sd

    def _record_fixed_duration(
        self,
        sd: Any,
        *,
        sample_rate: int,
        channels: int,
        device: int | str | None,
        duration: float,
        pre_roll_audio: PcmAudioBuffer | None,
    ):
        frames = int(duration * sample_rate)
        LOGGER.info(
            "开始固定时长录音：duration=%s sample_rate=%s channels=%s device=%s",
            duration,
            sample_rate,
            channels,
            device,
        )
        audio = sd.rec(frames, samplerate=sample_rate, channels=channels, device=device, dtype="int16")
        sd.wait()
        return self._prepend_pre_roll(audio, pre_roll_audio, sample_rate, channels)

    def _record_until_silence(
        self,
        sd: Any,
        *,
        sample_rate: int,
        channels: int,
        device: int | str | None,
        max_duration: float,
        pre_roll_audio: PcmAudioBuffer | None,
    ):
        import numpy as np

        block_seconds = float(
            self.config.get("recording.block_seconds", self.config.get("post_wake_speech.block_seconds", 0.2))
        )
        min_duration_seconds = float(self.config.get("recording.min_duration_seconds", 1.0))
        silence_duration_seconds = float(self.config.get("recording.silence_duration_seconds", 0.8))
        silence_rms_threshold = int(
            self.config.get(
                "recording.silence_rms_threshold",
                self.config.get("post_wake_speech.rms_threshold", 500),
            )
        )
        block_size = max(1, int(sample_rate * block_seconds))
        required_silent_blocks = max(1, int(math.ceil(silence_duration_seconds / block_seconds)))
        pre_roll_bytes = self._extract_pre_roll_bytes(pre_roll_audio, sample_rate=sample_rate, channels=channels)
        captured_chunks: list[bytes] = [pre_roll_bytes] if pre_roll_bytes else []
        total_bytes = len(pre_roll_bytes)
        speech_started = bool(pre_roll_bytes)
        silent_blocks = 0
        deadline = time.monotonic() + max_duration

        self._drain_audio_queue()
        LOGGER.info(
            "开始按静音自动收尾录音：max_duration=%ss min_duration=%ss silence=%ss threshold=%s sample_rate=%s channels=%s device=%s pre_roll=%.2fs",
            max_duration,
            min_duration_seconds,
            silence_duration_seconds,
            silence_rms_threshold,
            sample_rate,
            channels,
            device,
            _pcm_bytes_duration_seconds(pre_roll_bytes, sample_rate=sample_rate, channels=channels),
        )

        with sd.RawInputStream(
            samplerate=sample_rate,
            blocksize=block_size,
            device=device,
            dtype="int16",
            channels=channels,
            callback=self._audio_callback,
        ):
            while time.monotonic() < deadline:
                remaining = max(0.0, deadline - time.monotonic())
                try:
                    data = self._audio_queue.get(timeout=min(block_seconds, remaining))
                except queue.Empty:
                    continue

                if not data:
                    continue

                captured_chunks.append(data)
                total_bytes += len(data)
                rms = _pcm16_rms(data)

                if rms >= silence_rms_threshold:
                    speech_started = True
                    silent_blocks = 0
                    continue

                if not speech_started:
                    continue

                total_duration = _pcm_byte_length_duration_seconds(
                    total_bytes,
                    sample_rate=sample_rate,
                    channels=channels,
                )
                if total_duration < min_duration_seconds:
                    continue

                silent_blocks += 1
                if silent_blocks >= required_silent_blocks:
                    LOGGER.info(
                        "检测到连续静音，结束本轮录音：duration=%.2fs silent_blocks=%s silence_duration=%.2fs",
                        total_duration,
                        silent_blocks,
                        silent_blocks * block_seconds,
                    )
                    break

        pcm_bytes = b"".join(captured_chunks)
        audio = np.frombuffer(pcm_bytes, dtype="<i2")
        usable_samples = (audio.size // channels) * channels
        if usable_samples <= 0:
            raise AudioInputError("没有录到有效音频数据。")
        return audio[:usable_samples].reshape(-1, channels)

    def _prepend_pre_roll(
        self,
        audio,
        pre_roll_audio: PcmAudioBuffer | None,
        sample_rate: int,
        channels: int,
    ):
        """Prepend audio captured by speech activity detection to avoid losing short phrases."""
        if pre_roll_audio is None or not pre_roll_audio.data:
            return audio

        if (
            pre_roll_audio.sample_rate != sample_rate
            or pre_roll_audio.channels != channels
            or pre_roll_audio.sample_width_bytes != 2
        ):
            LOGGER.warning(
                "预录音参数与正式录音不一致，已跳过拼接：pre_roll=%sHz/%sch/%sbytes recording=%sHz/%sch",
                pre_roll_audio.sample_rate,
                pre_roll_audio.channels,
                pre_roll_audio.sample_width_bytes,
                sample_rate,
                channels,
            )
            return audio

        try:
            import numpy as np

            pre_roll = np.frombuffer(pre_roll_audio.data, dtype="<i2")
            usable_samples = (pre_roll.size // channels) * channels
            if usable_samples == 0:
                return audio
            pre_roll = pre_roll[:usable_samples].reshape(-1, channels)
            if getattr(audio, "ndim", 1) == 1:
                audio = audio.reshape(-1, channels)
            combined = np.concatenate([pre_roll, audio], axis=0)
            LOGGER.info("已拼接预录音：pre_roll=%.2fs", len(pre_roll) / float(sample_rate))
            return combined
        except Exception as exc:
            LOGGER.warning("预录音拼接失败，将仅保留正式录音：%s", exc)
            return audio

    def _extract_pre_roll_bytes(
        self,
        pre_roll_audio: PcmAudioBuffer | None,
        *,
        sample_rate: int,
        channels: int,
    ) -> bytes:
        """Return compatible pre-roll PCM bytes or an empty buffer."""
        if pre_roll_audio is None or not pre_roll_audio.data:
            return b""

        if (
            pre_roll_audio.sample_rate != sample_rate
            or pre_roll_audio.channels != channels
            or pre_roll_audio.sample_width_bytes != 2
        ):
            LOGGER.warning(
                "预录音参数与正式录音不一致，已跳过拼接：pre_roll=%sHz/%sch/%sbytes recording=%sHz/%sch",
                pre_roll_audio.sample_rate,
                pre_roll_audio.channels,
                pre_roll_audio.sample_width_bytes,
                sample_rate,
                channels,
            )
            return b""
        return pre_roll_audio.data

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            LOGGER.warning("录音音频输入状态：%s", status)
        self._audio_queue.put(bytes(indata))

    def _drain_audio_queue(self) -> None:
        while True:
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                return


def _pcm16_rms(data: bytes) -> int:
    """Calculate RMS for little-endian signed 16-bit PCM bytes."""
    if len(data) < 2:
        return 0

    usable_length = len(data) - (len(data) % 2)
    if usable_length <= 0:
        return 0

    sample_count = usable_length // 2
    total = 0
    for offset in range(0, usable_length, 2):
        sample = int.from_bytes(data[offset : offset + 2], byteorder="little", signed=True)
        total += sample * sample
    return int((total / sample_count) ** 0.5)


def _pcm_bytes_duration_seconds(data: bytes, *, sample_rate: int, channels: int) -> float:
    """Return PCM16 duration from raw bytes."""
    return _pcm_byte_length_duration_seconds(len(data), sample_rate=sample_rate, channels=channels)


def _pcm_byte_length_duration_seconds(byte_length: int, *, sample_rate: int, channels: int) -> float:
    """Return PCM16 duration from byte length."""
    if sample_rate <= 0 or channels <= 0:
        return 0.0
    frame_bytes = 2 * channels
    if frame_bytes <= 0:
        return 0.0
    return (byte_length / frame_bytes) / float(sample_rate)
