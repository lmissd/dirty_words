"""Offline wake word detector powered by Vosk."""

from __future__ import annotations

import json
import logging
import queue
from pathlib import Path

from modules.utils.config_loader import AppConfig
from modules.utils.errors import AudioInputError, ConfigurationError
from modules.wakeword.base import WakeEvent, WakeWordDetector
from modules.wakeword.stt_wakeword import match_wake_word

LOGGER = logging.getLogger(__name__)


class VoskWakeWordDetector(WakeWordDetector):
    """Detect Chinese wake words locally using a Vosk speech model."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.wake_words = [str(word) for word in config.get("wakeword.wake_words", ["范小团"])]
        self.sample_rate = int(config.get("wakeword.sample_rate", config.get("recording.sample_rate", 16000)))
        self.channels = int(config.get("wakeword.channels", config.get("recording.channels", 1)))
        self.device = config.get("wakeword.device", config.get("recording.device", None))
        self.block_size = int(config.get("wakeword.block_size", 8000))
        self.model_path = Path(str(config.get("wakeword.model_path", "models/vosk-model-small-cn-0.22")))
        self.grammar_enabled = bool(config.get("wakeword.grammar_enabled", True))
        self._audio_queue: queue.Queue[bytes] = queue.Queue()

        self.vosk_model = self._load_model()

    def wait_for_wake(self) -> WakeEvent:
        """Listen locally until a configured wake word is detected."""
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer
        except ImportError as exc:
            raise ConfigurationError("缺少 Vosk 依赖，请先执行 pip install -r requirements.txt") from exc

        recognizer = self._build_recognizer(KaldiRecognizer)
        LOGGER.info("开始 Vosk 本地离线唤醒监听：%s", self.wake_words)

        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                device=self.device,
                dtype="int16",
                channels=self.channels,
                callback=self._audio_callback,
            ):
                while True:
                    data = self._audio_queue.get()
                    text = self._recognize_chunk(recognizer, data)
                    matched = match_wake_word(text, self.wake_words)
                    if matched is not None:
                        LOGGER.info("检测到本地离线唤醒词：%s", matched)
                        return WakeEvent(wake_word=matched)
        except AudioInputError:
            raise
        except Exception as exc:
            raise AudioInputError(f"Vosk 本地唤醒监听失败，请检查麦克风：{exc}") from exc

    def _load_model(self):
        if not self.model_path.exists():
            raise ConfigurationError(
                f"Vosk 中文模型不存在：{self.model_path}。请先运行 python scripts/download_vosk_model.py"
            )

        try:
            from vosk import Model, SetLogLevel

            SetLogLevel(-1)
            return Model(str(self.model_path))
        except ImportError as exc:
            raise ConfigurationError("缺少 Vosk 依赖，请先执行 pip install -r requirements.txt") from exc

    def _build_recognizer(self, recognizer_class):
        if self.grammar_enabled:
            grammar = json.dumps([*self.wake_words, "[unk]"], ensure_ascii=False)
            return recognizer_class(self.vosk_model, self.sample_rate, grammar)
        return recognizer_class(self.vosk_model, self.sample_rate)

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            LOGGER.warning("Vosk 音频输入状态：%s", status)
        self._audio_queue.put(bytes(indata))

    def _recognize_chunk(self, recognizer, data: bytes) -> str:
        if recognizer.AcceptWaveform(data):
            text = _extract_vosk_text(recognizer.Result(), "text")
            if text:
                LOGGER.info("Vosk 识别结果：%s", text)
            return text

        partial = _extract_vosk_text(recognizer.PartialResult(), "partial")
        if partial:
            LOGGER.debug("Vosk 部分识别：%s", partial)
        return partial


def _extract_vosk_text(payload: str, key: str) -> str:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return ""
    value = data.get(key, "")
    return str(value)
