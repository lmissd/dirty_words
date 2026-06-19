"""Offline speech-to-text adapter powered by Vosk."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from modules.speech_to_text.base import SpeechToTextProvider
from modules.utils.config_loader import AppConfig
from modules.utils.errors import ApiError, ConfigurationError

LOGGER = logging.getLogger(__name__)


class VoskSpeechToText(SpeechToTextProvider):
    """Transcribe recorded audio locally with a Vosk Chinese model."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.sample_rate = int(config.get("speech_to_text.sample_rate", config.get("recording.sample_rate", 16000)))
        self.chunk_size = int(config.get("speech_to_text.chunk_size", 4000))
        self.model_path = Path(
            str(
                config.get(
                    "speech_to_text.model_path",
                    config.get("wakeword.model_path", "models/vosk-model-small-cn-0.22"),
                )
            )
        )
        self.model = self._load_model()

    def transcribe(self, audio_path: Path) -> str:
        """Transcribe a WAV file using the configured local Vosk model."""
        try:
            from vosk import KaldiRecognizer
        except ImportError as exc:
            raise ConfigurationError("缺少 Vosk 依赖，请先执行 pip install -r requirements.txt") from exc

        audio = _load_audio(audio_path, self.sample_rate)
        recognizer = KaldiRecognizer(self.model, self.sample_rate)
        segments: list[str] = []

        for start in range(0, len(audio), self.chunk_size):
            chunk = audio[start : start + self.chunk_size]
            if len(chunk) == 0:
                continue
            if recognizer.AcceptWaveform(chunk.tobytes()):
                text = _extract_vosk_text(recognizer.Result(), "text")
                if text:
                    segments.append(text)

        final_text = _extract_vosk_text(recognizer.FinalResult(), "text")
        if final_text:
            segments.append(final_text)

        text = " ".join(part.strip() for part in segments if part.strip()).strip()
        if not text:
            raise ApiError("本地语音识别未识别到有效文本。")

        LOGGER.info("Vosk 本地语音识别完成：%s", text)
        return text

    def _load_model(self):
        if not self.model_path.exists():
            raise ConfigurationError(
                f"Vosk 语音识别模型不存在：{self.model_path}。请先运行 python scripts/download_vosk_model.py"
            )

        try:
            from vosk import Model, SetLogLevel

            SetLogLevel(-1)
            return Model(str(self.model_path))
        except ImportError as exc:
            raise ConfigurationError("缺少 Vosk 依赖，请先执行 pip install -r requirements.txt") from exc


def _load_audio(audio_path: Path, target_sample_rate: int) -> np.ndarray:
    """Load WAV audio and convert it to mono PCM16 at the target sample rate."""
    try:
        import soundfile as sf
    except ImportError as exc:
        raise ConfigurationError("缺少 soundfile 依赖，请先执行 pip install -r requirements.txt") from exc

    try:
        audio, sample_rate = sf.read(str(audio_path), dtype="float32", always_2d=False)
    except Exception as exc:
        raise ApiError(f"读取录音文件失败：{exc}") from exc

    if isinstance(audio, np.ndarray) and audio.ndim > 1:
        audio = audio.mean(axis=1)

    mono_audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    if mono_audio.size == 0:
        raise ApiError("录音文件为空，无法进行语音识别。")

    if sample_rate != target_sample_rate:
        mono_audio = _resample_audio(mono_audio, sample_rate, target_sample_rate)

    pcm16 = np.clip(mono_audio, -1.0, 1.0)
    return (pcm16 * 32767.0).astype(np.int16)


def _resample_audio(audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    """Resample mono audio with linear interpolation."""
    if source_rate == target_rate or audio.size == 0:
        return audio.astype(np.float32, copy=False)

    duration = audio.shape[0] / float(source_rate)
    target_length = max(1, int(round(duration * target_rate)))
    source_positions = np.linspace(0.0, duration, num=audio.shape[0], endpoint=False)
    target_positions = np.linspace(0.0, duration, num=target_length, endpoint=False)
    resampled = np.interp(target_positions, source_positions, audio)
    return resampled.astype(np.float32, copy=False)


def _extract_vosk_text(payload: str, key: str) -> str:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return ""
    return str(data.get(key, "")).strip()
