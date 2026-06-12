"""sounddevice-based WAV recorder."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from modules.recorder.base import AudioRecorder, RecordedAudio
from modules.utils.audio_devices import resolve_input_device
from modules.utils.config_loader import AppConfig
from modules.utils.disk import ensure_free_space
from modules.utils.errors import AudioInputError

LOGGER = logging.getLogger(__name__)


class SoundDeviceRecorder(AudioRecorder):
    """Record microphone audio to a temporary WAV file."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def record(self) -> RecordedAudio:
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
            audio = sd.rec(frames, samplerate=sample_rate, channels=channels, device=device)
            sd.wait()
            sf.write(output_path, audio, sample_rate)
            LOGGER.info("录音完成：%s", output_path)
            return RecordedAudio(path=output_path, duration_seconds=duration, sample_rate=sample_rate)
        except Exception as exc:
            raise AudioInputError(f"录音失败，请检查麦克风：{exc}") from exc
