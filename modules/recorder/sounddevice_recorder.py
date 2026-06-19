"""sounddevice-based WAV recorder."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from modules.recorder.base import AudioRecorder, PcmAudioBuffer, RecordedAudio
from modules.utils.audio_devices import resolve_input_device
from modules.utils.config_loader import AppConfig
from modules.utils.disk import ensure_free_space
from modules.utils.errors import AudioInputError

LOGGER = logging.getLogger(__name__)


class SoundDeviceRecorder(AudioRecorder):
    """Record microphone audio to a temporary WAV file."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def record(self, pre_roll_audio: PcmAudioBuffer | None = None) -> RecordedAudio:
        """Record a WAV file using the configured microphone."""
        duration = float(self.config.get("recording.duration_seconds", 7))
        sample_rate = int(self.config.get("recording.sample_rate", 16000))
        channels = int(self.config.get("recording.channels", 1))
        output_dir = Path(str(self.config.get("paths.audio_temp_dir", "recordings")))
        ensure_free_space(output_dir)

        filename = datetime.now().strftime("recording_%Y%m%d_%H%M%S.wav")
        output_path = output_dir / filename
        frames = int(duration * sample_rate)

        try:
            import sounddevice as sd
            import soundfile as sf

            device = resolve_input_device(
                self.config,
                "recording.device",
                channels=channels,
                sd_module=sd,
            )
            LOGGER.info(
                "开始录音：duration=%s sample_rate=%s channels=%s device=%s",
                duration,
                sample_rate,
                channels,
                device,
            )
            audio = sd.rec(frames, samplerate=sample_rate, channels=channels, device=device, dtype="int16")
            sd.wait()
            audio = self._prepend_pre_roll(audio, pre_roll_audio, sample_rate, channels)
            sf.write(output_path, audio, sample_rate, subtype="PCM_16")
            LOGGER.info("录音完成：%s", output_path)
            actual_duration = len(audio) / float(sample_rate)
            return RecordedAudio(path=output_path, duration_seconds=actual_duration, sample_rate=sample_rate)
        except Exception as exc:
            raise AudioInputError(f"录音失败，请检查麦克风：{exc}") from exc

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
