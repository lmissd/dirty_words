"""Application orchestration for the Civil Language Robot."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from modules.display.base import Display
from modules.display.console_display import ConsoleDisplay
from modules.display.tkinter_display import TkinterDisplay
from modules.llm.base import CivilLanguageAnalyzer
from modules.llm.deepseek_civil_analyzer import DeepSeekCivilLanguageAnalyzer
from modules.llm.openai_civil_analyzer import OpenAICivilLanguageAnalyzer
from modules.recorder.base import AudioRecorder, RecordedAudio
from modules.recorder.sounddevice_recorder import SoundDeviceRecorder
from modules.speech_to_text.base import SpeechToTextProvider
from modules.speech_to_text.openai_stt import OpenAISpeechToText
from modules.tts.base import TextToSpeechProvider
from modules.tts.openai_tts import OpenAITextToSpeech
from modules.utils.audio_player import AudioPlayer
from modules.utils.config_loader import AppConfig, load_config
from modules.utils.errors import ConfigurationError, RobotError
from modules.utils.logging_setup import setup_logging
from modules.wakeword.base import WakeWordDetector
from modules.wakeword.console_wakeword import ConsoleWakeWordDetector
from modules.wakeword.stt_wakeword import SttWakeWordDetector
from modules.wakeword.vosk_wakeword import VoskWakeWordDetector

LOGGER = logging.getLogger(__name__)


class CivilLanguageRobotApp:
    """Run the wake-record-analyze-speak state machine."""

    def __init__(
        self,
        config: AppConfig,
        wakeword: WakeWordDetector,
        recorder: AudioRecorder,
        speech_to_text: SpeechToTextProvider,
        analyzer: CivilLanguageAnalyzer,
        display: Display,
        tts: TextToSpeechProvider,
    ) -> None:
        self.config = config
        self.wakeword = wakeword
        self.recorder = recorder
        self.speech_to_text = speech_to_text
        self.analyzer = analyzer
        self.display = display
        self.tts = tts
        self._logger = logging.getLogger(self.__class__.__name__)

    def run_forever(self) -> None:
        """Run the robot loop until interrupted."""
        self._logger.info("文明用语机器人启动，进入长期待机。")
        while True:
            self.run_once()
            time.sleep(float(self.config.get("app.cycle_pause_seconds", 2)))

    def run_once(self) -> None:
        """Run one full interaction cycle and recover from handled errors."""
        audio: RecordedAudio | None = None
        try:
            self.display.show_standby(self.config.get("wakeword.wake_words", []))
            self.wakeword.wait_for_wake()

            self.display.show_status("已唤醒，开始录音。")
            audio = self.recorder.record()

            self.display.show_status("正在识别语音。")
            user_text = self.speech_to_text.transcribe(audio.path)

            self.display.show_status("正在分析文明程度。")
            analysis = self.analyzer.analyze(user_text)

            self.display.show_result(user_text, analysis)
            self.tts.speak(_format_tts_text(analysis.reason, analysis.suggestion))
        except RobotError as exc:
            self._logger.warning("本轮流程发生可恢复错误：%s", exc)
            self.display.show_error(str(exc))
            time.sleep(float(self.config.get("app.max_error_pause_seconds", 5)))
        except Exception as exc:
            self._logger.exception("本轮流程发生未知错误。")
            self.display.show_error("系统遇到未知错误，正在返回待机。")
            time.sleep(float(self.config.get("app.max_error_pause_seconds", 5)))
            self._logger.debug("未知错误详情：%s", exc)
        finally:
            if audio is not None:
                self._cleanup_audio(audio.path)

    def _cleanup_audio(self, audio_path: Path) -> None:
        keep_recordings = bool(self.config.get("privacy.keep_recordings", False))
        if keep_recordings:
            self._logger.info("保留录音文件：%s", audio_path)
            return

        try:
            if audio_path.exists():
                audio_path.unlink()
                self._logger.info("已删除临时录音：%s", audio_path)
        except OSError as exc:
            self._logger.warning("删除临时录音失败：%s", exc)


class WakeGreetingApp:
    """Run wake word detection and greet the child without downstream analysis."""

    def __init__(
        self,
        config: AppConfig,
        wakeword: WakeWordDetector,
        display: Display,
        tts: TextToSpeechProvider,
    ) -> None:
        self.config = config
        self.wakeword = wakeword
        self.display = display
        self.tts = tts
        self._logger = logging.getLogger(self.__class__.__name__)

    def run_forever(self) -> None:
        """Keep greeting after each wake event until interrupted."""
        self._logger.info("唤醒问候模式启动。")
        while True:
            self.run_once()
            time.sleep(float(self.config.get("app.cycle_pause_seconds", 2)))

    def run_once(self) -> None:
        """Wait for one wake event, speak the greeting, and return."""
        try:
            wake_words = list(self.config.get("wakeword.wake_words", []))
            greeting_text = str(self.config.get("greeting.text", "小朋友你好"))

            self.display.show_standby(wake_words)
            event = self.wakeword.wait_for_wake()
            self.display.show_status(f"唤醒成功：{event.wake_word}")

            self._logger.info("播放问候语：%s", greeting_text)
            self.tts.speak(greeting_text)
            self.display.show_status("问候完成，返回待机。")
        except RobotError as exc:
            self._logger.warning("唤醒问候流程发生可恢复错误：%s", exc)
            self.display.show_error(str(exc))
            time.sleep(float(self.config.get("app.max_error_pause_seconds", 5)))
        except Exception:
            self._logger.exception("唤醒问候流程发生未知错误。")
            self.display.show_error("问候流程遇到未知错误，正在返回待机。")
            time.sleep(float(self.config.get("app.max_error_pause_seconds", 5)))


def build_app(config_path: Path) -> CivilLanguageRobotApp:
    """Build the application from configuration."""
    config = load_config(config_path)
    setup_logging(config)
    LOGGER.info("配置加载完成：%s", config_path)

    display = _build_display(config)
    audio_player = AudioPlayer(config)
    speech_to_text = _build_speech_to_text(config)

    return CivilLanguageRobotApp(
        config=config,
        wakeword=_build_wakeword(config, speech_to_text),
        recorder=_build_recorder(config),
        speech_to_text=speech_to_text,
        analyzer=_build_analyzer(config),
        display=display,
        tts=_build_tts(config, audio_player),
    )


def build_wake_greeting_app(config_path: Path) -> WakeGreetingApp:
    """Build the wake-greeting application from configuration."""
    config = load_config(config_path)
    setup_logging(config)
    LOGGER.info("唤醒问候配置加载完成：%s", config_path)

    wakeword_engine = str(config.get("wakeword.engine", "console")).lower()
    speech_to_text = _build_speech_to_text(config) if wakeword_engine == "stt" else None
    audio_player = AudioPlayer(config)

    return WakeGreetingApp(
        config=config,
        wakeword=_build_wakeword(config, speech_to_text),
        display=_build_display(config),
        tts=_build_tts(config, audio_player),
    )


def run_wakeword_test(config_path: Path) -> None:
    """Run wake word detection without building API-backed modules."""
    config = load_config(config_path)
    setup_logging(config)
    display = _build_display(config)
    wakeword_engine = str(config.get("wakeword.engine", "console")).lower()
    speech_to_text = _build_speech_to_text(config) if wakeword_engine == "stt" else None
    wakeword = _build_wakeword(config, speech_to_text)

    display.show_standby(list(config.get("wakeword.wake_words", [])))
    event = wakeword.wait_for_wake()
    display.show_status(f"唤醒成功：{event.wake_word}")


def _build_wakeword(
    config: AppConfig,
    speech_to_text: SpeechToTextProvider | None = None,
) -> WakeWordDetector:
    engine = str(config.get("wakeword.engine", "console")).lower()
    if engine == "console":
        return ConsoleWakeWordDetector(
            wake_words=list(config.get("wakeword.wake_words", ["小文小文"])),
            prompt=str(config.get("wakeword.prompt", "输入唤醒词并回车。")),
        )
    if engine == "stt":
        if speech_to_text is None:
            raise ConfigurationError("STT 唤醒需要先配置语音识别模块。")
        return SttWakeWordDetector(config, speech_to_text)
    if engine in {"vosk", "local"}:
        return VoskWakeWordDetector(config)
    raise ConfigurationError(f"暂不支持的唤醒词引擎：{engine}")


def _build_recorder(config: AppConfig) -> AudioRecorder:
    engine = str(config.get("recording.engine", "sounddevice")).lower()
    if engine == "sounddevice":
        return SoundDeviceRecorder(config)
    raise ConfigurationError(f"暂不支持的录音引擎：{engine}")


def _build_speech_to_text(config: AppConfig) -> SpeechToTextProvider:
    provider = str(config.get("speech_to_text.provider", "openai")).lower()
    if provider == "openai":
        return OpenAISpeechToText(config)
    raise ConfigurationError(f"暂不支持的语音识别供应商：{provider}")


def _build_analyzer(config: AppConfig) -> CivilLanguageAnalyzer:
    provider = str(config.get("llm.provider", "openai")).lower()
    if provider == "openai":
        return OpenAICivilLanguageAnalyzer(config)
    if provider == "deepseek":
        return DeepSeekCivilLanguageAnalyzer(config)
    raise ConfigurationError(f"暂不支持的大模型供应商：{provider}")


def _build_tts(config: AppConfig, audio_player: AudioPlayer) -> TextToSpeechProvider:
    provider = str(config.get("tts.provider", "openai")).lower()
    if provider == "openai":
        return OpenAITextToSpeech(config, audio_player)
    raise ConfigurationError(f"暂不支持的 TTS 供应商：{provider}")


def _build_display(config: AppConfig) -> Display:
    engine = str(config.get("display.engine", "console")).lower()
    if engine == "console":
        return ConsoleDisplay(config)
    if engine == "tkinter":
        return TkinterDisplay(config)
    raise ConfigurationError(f"暂不支持的显示引擎：{engine}")


def _format_tts_text(reason: str, suggestion: str) -> str:
    return f"检测完成。{reason}。建议：{suggestion}"
