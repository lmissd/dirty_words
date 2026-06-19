"""Speech-to-text wake word detector."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from modules.speech_to_text.base import SpeechToTextProvider
from modules.utils.audio_devices import resolve_input_device
from modules.utils.config_loader import AppConfig
from modules.utils.disk import ensure_free_space
from modules.utils.errors import ApiError, AudioInputError
from modules.wakeword.base import WakeEvent, WakeWordDetector
from modules.wakeword.matcher import WakeMatcherConfig, match_wake_phrase

LOGGER = logging.getLogger(__name__)


class SttWakeWordDetector(WakeWordDetector):
    """Detect wake words by transcribing short microphone chunks."""

    def __init__(self, config: AppConfig, speech_to_text: SpeechToTextProvider) -> None:
        self.config = config
        self.speech_to_text = speech_to_text
        self.wake_words = [str(word) for word in config.get("wakeword.wake_words", ["范小团你好"])]
        self.matcher_config = WakeMatcherConfig.from_app_config(config)
        self.listen_seconds = float(config.get("wakeword.listen_seconds", 2.5))
        self.idle_pause_seconds = float(config.get("wakeword.idle_pause_seconds", 0.2))
        self.sample_rate = int(config.get("wakeword.sample_rate", config.get("recording.sample_rate", 16000)))
        self.channels = int(config.get("wakeword.channels", config.get("recording.channels", 1)))
        self.device = config.get("wakeword.device", config.get("recording.device", None))
        self.delete_chunks = bool(config.get("wakeword.delete_chunks", True))
        self.output_dir = Path(str(config.get("paths.audio_temp_dir", "recordings")))

    def wait_for_wake(self, on_ready: Callable[[], None] | None = None) -> WakeEvent:
        """Continuously listen until a configured wake word is heard."""
        LOGGER.info("开始 STT 语音唤醒监听：%s", self.wake_words)
        if on_ready is not None:
            on_ready()
        while True:
            chunk_path = self._record_chunk()
            try:
                try:
                    transcript = self.speech_to_text.transcribe(chunk_path)
                except ApiError as exc:
                    LOGGER.info("本轮唤醒片段未识别到有效文本，继续监听：%s", exc)
                    time.sleep(self.idle_pause_seconds)
                    continue
                matched = match_wake_phrase(transcript, self.matcher_config)
                LOGGER.info("唤醒词片段识别：%s", transcript)
                if matched is not None:
                    LOGGER.info("检测到语音唤醒词：%s", matched)
                    return WakeEvent(wake_word=matched)
            finally:
                if self.delete_chunks:
                    _safe_unlink(chunk_path)
            time.sleep(self.idle_pause_seconds)

    def _record_chunk(self) -> Path:
        ensure_free_space(self.output_dir)
        output_path = self.output_dir / datetime.now().strftime("wakeword_%Y%m%d_%H%M%S_%f.wav")
        frames = int(self.listen_seconds * self.sample_rate)

        try:
            import sounddevice as sd
            import soundfile as sf

            device = resolve_input_device(
                self.config,
                "wakeword.device",
                fallback_key="recording.device",
                channels=self.channels,
                sd_module=sd,
            )
            LOGGER.info(
                "录制唤醒词片段：seconds=%s sample_rate=%s channels=%s device=%s",
                self.listen_seconds,
                self.sample_rate,
                self.channels,
                device,
            )
            audio = sd.rec(
                frames,
                samplerate=self.sample_rate,
                channels=self.channels,
                device=device,
            )
            sd.wait()
            sf.write(output_path, audio, self.sample_rate)
            return output_path
        except Exception as exc:
            raise AudioInputError(f"唤醒词录音失败，请检查麦克风：{exc}") from exc


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError as exc:
        LOGGER.warning("删除唤醒词临时音频失败：%s", exc)
