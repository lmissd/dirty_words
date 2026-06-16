"""Offline wake word detector powered by openWakeWord."""

from __future__ import annotations

import logging
import queue
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

from modules.utils.audio_devices import resolve_input_device
from modules.utils.config_loader import AppConfig
from modules.utils.errors import AudioInputError, ConfigurationError
from modules.wakeword.base import WakeEvent, WakeWordDetector

LOGGER = logging.getLogger(__name__)

_DEFAULT_MODEL_PATH = "models/openwakeword/fantuan_fantuan.onnx"
_OPENWAKEWORD_SAMPLE_RATE = 16000
_DEFAULT_FRAME_MS = 80


class OpenWakeWordDetector(WakeWordDetector):
    """Detect a custom local wake phrase with openWakeWord."""

    def __init__(
        self,
        config: AppConfig,
        *,
        model_factory: Callable[..., Any] | None = None,
        sd_module: Any | None = None,
    ) -> None:
        self.config = config
        self.display_wake_word = str(config.get("wakeword.display_wake_word", "饭团饭团"))
        self.input_sample_rate = int(
            config.get("wakeword.input_sample_rate", config.get("wakeword.sample_rate", 48000))
        )
        self.model_sample_rate = int(config.get("wakeword.model_sample_rate", _OPENWAKEWORD_SAMPLE_RATE))
        self.frame_ms = int(config.get("wakeword.frame_ms", _DEFAULT_FRAME_MS))
        self.channels = int(config.get("wakeword.channels", config.get("recording.channels", 1)))
        self.threshold = float(config.get("wakeword.threshold", 0.5))
        self.patience_frames = max(1, int(config.get("wakeword.patience_frames", 1)))
        self.debounce_seconds = max(0.0, float(config.get("wakeword.debounce_seconds", 1.5)))
        self.inference_framework = str(config.get("wakeword.inference_framework", "onnx")).lower()
        self.noise_suppression_enabled = bool(config.get("wakeword.noise_suppression_enabled", True))
        self.noise_suppression_fallback = bool(config.get("wakeword.noise_suppression_fallback", True))
        self.vad_enabled = bool(config.get("wakeword.vad_enabled", True))
        default_vad_threshold = 0.35 if self.vad_enabled else 0.0
        self.vad_threshold = float(config.get("wakeword.vad_threshold", default_vad_threshold))
        if not self.vad_enabled:
            self.vad_threshold = 0.0
        self.log_scores = bool(config.get("wakeword.log_scores", False))
        self.score_log_interval_seconds = float(config.get("wakeword.score_log_interval_seconds", 1.0))
        self.allow_pretrained_models = bool(config.get("wakeword.allow_pretrained_models", False))
        self.model_specs = _string_list(config.get("wakeword.model_paths", [_DEFAULT_MODEL_PATH]))
        self.target_labels = _string_list(config.get("wakeword.target_labels", [])) or [
            _model_label_from_spec(spec) for spec in self.model_specs
        ]

        if self.model_sample_rate != _OPENWAKEWORD_SAMPLE_RATE:
            raise ConfigurationError("openWakeWord 需要 16000Hz 模型输入，请保持 wakeword.model_sample_rate: 16000")

        self.input_frame_samples = frame_sample_count(self.input_sample_rate, self.frame_ms)
        self.model_frame_samples = frame_sample_count(self.model_sample_rate, self.frame_ms)
        self._audio_queue: queue.Queue[bytes] = queue.Queue()
        self._model_audio_buffer = np.empty(0, dtype=np.int16)
        self._hit_counts: dict[str, int] = {}
        self._last_trigger_time = 0.0
        self._last_score_log_time = 0.0
        self._model_factory = model_factory
        self._sd_module = sd_module
        self._model: Any | None = None

    def wait_for_wake(self) -> WakeEvent:
        """Listen until openWakeWord reports the configured wake phrase."""
        sd = self._load_sounddevice()
        model = self._load_model()
        self._reset_runtime_state(model)
        device = resolve_input_device(
            self.config,
            "wakeword.device",
            fallback_key="recording.device",
            channels=self.channels,
            sd_module=sd,
        )

        LOGGER.info(
            "开始 openWakeWord 本地唤醒监听：%s input=%sHz model=%sHz frame=%sms threshold=%.2f vad=%.2f",
            self.display_wake_word,
            self.input_sample_rate,
            self.model_sample_rate,
            self.frame_ms,
            self.threshold,
            self.vad_threshold,
        )

        try:
            with sd.RawInputStream(
                samplerate=self.input_sample_rate,
                blocksize=self.input_frame_samples,
                device=device,
                dtype="int16",
                channels=self.channels,
                callback=self._audio_callback,
            ):
                while True:
                    data = self._audio_queue.get()
                    for frame in self._prepare_model_frames(data):
                        predictions = model.predict(frame)
                        matched_label = self._match_predictions(predictions)
                        if matched_label is not None:
                            LOGGER.info(
                                "openWakeWord 检测到唤醒词：%s label=%s",
                                self.display_wake_word,
                                matched_label,
                            )
                            return WakeEvent(wake_word=self.display_wake_word)
        except AudioInputError:
            raise
        except Exception as exc:
            raise AudioInputError(f"openWakeWord 唤醒监听失败，请检查麦克风或模型配置：{exc}") from exc

    def _load_sounddevice(self) -> Any:
        if self._sd_module is not None:
            return self._sd_module
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise AudioInputError("缺少 sounddevice 依赖，请先执行 pip install -r requirements.txt") from exc
        return sd

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        model_specs = self._validate_model_specs()
        factory = self._model_factory
        if factory is None:
            try:
                from openwakeword.model import Model
            except ImportError as exc:
                raise ConfigurationError("缺少 openWakeWord 依赖，请先安装 openwakeword。") from exc
            factory = Model

        kwargs = {
            "wakeword_models": model_specs,
            "enable_speex_noise_suppression": self.noise_suppression_enabled,
            "vad_threshold": self.vad_threshold,
            "inference_framework": self.inference_framework,
        }

        try:
            self._model = factory(**kwargs)
        except ModuleNotFoundError as exc:
            if self._can_retry_without_noise_suppression(exc):
                LOGGER.warning("Speex 噪声抑制依赖缺失，已自动关闭噪声抑制后重试：%s", exc)
                kwargs["enable_speex_noise_suppression"] = False
                self._model = factory(**kwargs)
            else:
                raise ConfigurationError(f"初始化 openWakeWord 模型失败：{exc}") from exc
        except Exception as exc:
            raise ConfigurationError(f"初始化 openWakeWord 模型失败：{exc}") from exc

        return self._model

    def _validate_model_specs(self) -> list[str]:
        if not self.model_specs:
            if self.allow_pretrained_models:
                return []
            raise ConfigurationError(
                "openWakeWord 需要 wakeword.model_paths 指向“饭团饭团”的自定义模型文件。"
            )

        if self.allow_pretrained_models:
            return self.model_specs

        missing_paths = [spec for spec in self.model_specs if not Path(spec).exists()]
        if missing_paths:
            missing = ", ".join(missing_paths)
            raise ConfigurationError(
                "openWakeWord 模型不存在："
                f"{missing}。请先放置针对“饭团饭团”训练好的 .onnx 或 .tflite 模型，"
                "或临时把 wakeword.engine 改回 vosk。"
            )
        return self.model_specs

    def _can_retry_without_noise_suppression(self, exc: ModuleNotFoundError) -> bool:
        missing_name = str(getattr(exc, "name", "") or exc)
        return (
            self.noise_suppression_enabled
            and self.noise_suppression_fallback
            and "speex" in missing_name.lower()
        )

    def _reset_runtime_state(self, model: Any) -> None:
        self._clear_audio_queue()
        self._model_audio_buffer = np.empty(0, dtype=np.int16)
        self._hit_counts.clear()
        if hasattr(model, "reset"):
            model.reset()

    def _clear_audio_queue(self) -> None:
        while True:
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                return

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            LOGGER.warning("openWakeWord 音频输入状态：%s", status)
        self._audio_queue.put(bytes(indata))

    def _prepare_model_frames(self, data: bytes) -> list[np.ndarray]:
        input_samples = pcm16_bytes_to_mono(data, self.channels)
        model_samples = resample_pcm16_mono(
            input_samples,
            source_rate=self.input_sample_rate,
            target_rate=self.model_sample_rate,
        )
        if self._model_audio_buffer.size:
            model_samples = np.concatenate((self._model_audio_buffer, model_samples))

        frames: list[np.ndarray] = []
        offset = 0
        while offset + self.model_frame_samples <= model_samples.size:
            frame = model_samples[offset : offset + self.model_frame_samples]
            frames.append(frame.astype(np.int16, copy=False))
            offset += self.model_frame_samples

        self._model_audio_buffer = model_samples[offset:].copy()
        return frames

    def _match_predictions(self, predictions: dict[str, Any]) -> str | None:
        self._log_predictions(predictions)
        target_labels = set(self.target_labels)
        now = time.monotonic()

        for label, raw_score in predictions.items():
            if target_labels and label not in target_labels:
                self._hit_counts[label] = 0
                continue

            score = float(raw_score)
            if score < self.threshold:
                self._hit_counts[label] = 0
                continue

            self._hit_counts[label] = self._hit_counts.get(label, 0) + 1
            if self._hit_counts[label] < self.patience_frames:
                continue

            if self.debounce_seconds and now - self._last_trigger_time < self.debounce_seconds:
                continue

            self._last_trigger_time = now
            return label

        return None

    def _log_predictions(self, predictions: dict[str, Any]) -> None:
        if not self.log_scores:
            return
        now = time.monotonic()
        if now - self._last_score_log_time < self.score_log_interval_seconds:
            return
        self._last_score_log_time = now
        formatted = ", ".join(f"{label}={float(score):.3f}" for label, score in predictions.items())
        LOGGER.info("openWakeWord 分数：%s", formatted)


def frame_sample_count(sample_rate: int, frame_ms: int) -> int:
    """Return the number of samples in one frame."""
    samples = sample_rate * frame_ms / 1000
    if samples != int(samples):
        raise ConfigurationError(f"{sample_rate}Hz 下无法整除 {frame_ms}ms 音频帧")
    return int(samples)


def pcm16_bytes_to_mono(data: bytes, channels: int) -> np.ndarray:
    """Convert little-endian PCM16 bytes to mono int16 samples."""
    if not data:
        return np.empty(0, dtype=np.int16)
    samples = np.frombuffer(data, dtype="<i2")
    if channels <= 1:
        return samples.astype(np.int16, copy=False)

    usable = samples.size - (samples.size % channels)
    if usable <= 0:
        return np.empty(0, dtype=np.int16)
    reshaped = samples[:usable].reshape(-1, channels).astype(np.float32)
    mono = np.rint(reshaped.mean(axis=1))
    return np.clip(mono, -32768, 32767).astype(np.int16)


def resample_pcm16_mono(samples: np.ndarray, *, source_rate: int, target_rate: int) -> np.ndarray:
    """Resample mono PCM16 audio with a lightweight deterministic path."""
    if samples.size == 0:
        return np.empty(0, dtype=np.int16)
    if source_rate == target_rate:
        return samples.astype(np.int16, copy=False)

    if source_rate > target_rate and source_rate % target_rate == 0:
        ratio = source_rate // target_rate
        usable = samples.size - (samples.size % ratio)
        if usable <= 0:
            return np.empty(0, dtype=np.int16)
        averaged = samples[:usable].reshape(-1, ratio).astype(np.float32).mean(axis=1)
        return np.clip(np.rint(averaged), -32768, 32767).astype(np.int16)

    target_length = max(1, int(round(samples.size * target_rate / source_rate)))
    old_positions = np.linspace(0.0, 1.0, num=samples.size, endpoint=False)
    new_positions = np.linspace(0.0, 1.0, num=target_length, endpoint=False)
    resampled = np.interp(new_positions, old_positions, samples.astype(np.float32))
    return np.clip(np.rint(resampled), -32768, 32767).astype(np.int16)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _model_label_from_spec(spec: str) -> str:
    path = Path(spec)
    if path.suffix:
        return path.stem
    return spec
