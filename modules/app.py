"""Application orchestration for the Civil Language Robot."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from modules.display.base import Display
from modules.display.console_display import ConsoleDisplay
from modules.display.robot_animation_display import RobotAnimationDisplay
from modules.display.tkinter_display import TkinterDisplay
from modules.llm.base import CivilLanguageAnalyzer
from modules.llm.deepseek_civil_analyzer import DeepSeekCivilLanguageAnalyzer
from modules.llm.openai_civil_analyzer import OpenAICivilLanguageAnalyzer
from modules.recorder.base import AudioRecorder, PcmAudioBuffer, RecordedAudio
from modules.recorder.speech_activity import SpeechActivityDetector
from modules.recorder.sounddevice_recorder import SoundDeviceRecorder
from modules.speech_to_text.base import SpeechToTextProvider
from modules.speech_to_text.openai_stt import OpenAISpeechToText
from modules.speech_to_text.static_stt import StaticSpeechToText
from modules.speech_to_text.vosk_stt import VoskSpeechToText
from modules.tts.base import TextToSpeechProvider
from modules.tts.local_command_tts import LocalCommandTextToSpeech
from modules.tts.local_audio_tts import LocalAudioTextToSpeech
from modules.tts.openai_tts import OpenAITextToSpeech
from modules.tts.piper_tts import PiperTextToSpeech
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
        speech_activity: SpeechActivityDetector | None = None,
        greeting_tts: TextToSpeechProvider | None = None,
    ) -> None:
        self.config = config
        self.wakeword = wakeword
        self.recorder = recorder
        self.speech_to_text = speech_to_text
        self.analyzer = analyzer
        self.display = display
        self.tts = tts
        self.speech_activity = speech_activity
        self.greeting_tts = greeting_tts or tts
        self._logger = logging.getLogger(self.__class__.__name__)

    def run_forever(self) -> None:
        """Run the robot loop until interrupted."""
        self._logger.info("文明用语机器人启动，进入长期待机。")
        while True:
            self.run_once()
            time.sleep(float(self.config.get("app.cycle_pause_seconds", 2)))

    def run_once(self) -> None:
        """Run one full interaction cycle and recover from handled errors."""
        try:
            wake_words = _display_wake_words(self.config)
            self.display.show_status("正在准备唤醒监听...")
            event = self.wakeword.wait_for_wake(on_ready=lambda: self.display.show_standby(wake_words))

            if bool(self.config.get("greeting.enabled_in_main_flow", True)):
                self._speak_during_wake_animation(event.wake_word)

            if self._should_run_continuous_session():
                self._run_continuous_post_wake_session()
            else:
                self._run_single_interaction_cycle()
        except RobotError as exc:
            self._logger.warning("本轮流程发生可恢复错误：%s", exc)
            self.display.show_error(str(exc))
            time.sleep(float(self.config.get("app.max_error_pause_seconds", 5)))
        except Exception as exc:
            self._logger.exception("本轮流程发生未知错误。")
            self.display.show_error("系统遇到未知错误，正在返回待机。")
            time.sleep(float(self.config.get("app.max_error_pause_seconds", 5)))
            self._logger.debug("未知错误详情：%s", exc)

    def _run_continuous_post_wake_session(self) -> None:
        """Keep listening after wake until no speech is detected within the timeout."""
        while True:
            if not self._wait_for_post_wake_speech():
                return
            pre_roll_audio = self._consume_post_wake_pre_roll()
            try:
                self._run_single_interaction_cycle(pre_roll_audio=pre_roll_audio)
            except RobotError as exc:
                self._logger.warning("本次语音处理失败，继续保持唤醒后的监听状态：%s", exc)
                self.display.show_status("这句话没有听清或处理失败，请再说一遍。")
                time.sleep(float(self.config.get("post_wake_speech.error_pause_seconds", 1)))

    def _run_single_interaction_cycle(self, pre_roll_audio: PcmAudioBuffer | None = None) -> None:
        """Record, transcribe, analyze, and optionally remind for one utterance."""
        audio: RecordedAudio | None = None
        try:
            self.display.show_status("已唤醒，开始录音。")
            audio = self.recorder.record(pre_roll_audio=pre_roll_audio)

            self.display.show_status("正在识别语音。")
            user_text = self.speech_to_text.transcribe(audio.path)

            self.display.show_status("正在分析文明程度。")
            analysis = self.analyzer.analyze(user_text)

            if not _should_remind(analysis, self.config):
                self.display.show_status("这次表达很文明，继续保持。")
                return

            self.display.show_result(user_text, analysis)
            self.tts.speak(_format_tts_text(user_text, analysis.reason, analysis.suggestion))
        finally:
            if audio is not None:
                self._cleanup_audio(audio.path)

    def _consume_post_wake_pre_roll(self) -> PcmAudioBuffer | None:
        """Return the audio captured during post-wake speech detection, if available."""
        if self.speech_activity is None:
            return None
        return getattr(self.speech_activity, "last_pre_roll_audio", None)

    def _should_run_continuous_session(self) -> bool:
        """Return True when the post-wake flow should stay active until silence timeout."""
        return (
            bool(self.config.get("post_wake_speech.enabled", True))
            and self.speech_activity is not None
            and bool(self.config.get("post_wake_speech.continuous_session", True))
        )

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

    def _wait_for_post_wake_speech(self) -> bool:
        enabled = bool(self.config.get("post_wake_speech.enabled", True))
        if not enabled:
            return True

        timeout_seconds = float(self.config.get("post_wake_speech.timeout_seconds", 30))
        if self.speech_activity is None:
            self._logger.warning("未配置语音活动检测器，跳过唤醒后等待语音。")
            return True

        self.display.show_status(f"已唤醒，请在 {int(timeout_seconds)} 秒内说话。")
        if self.speech_activity.wait_for_speech(timeout_seconds):
            return True

        self.display.show_status("没有听到新的语音，返回待机。")
        return False

    def _speak_during_wake_animation(self, wake_word: str) -> None:
        greeting_text = str(self.config.get("greeting.text", "小朋友你好"))
        errors: list[Exception] = []

        def speak_greeting() -> None:
            try:
                self._logger.info("播放唤醒问候语：%s", greeting_text)
                self.greeting_tts.speak(greeting_text)
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=speak_greeting, name="civil-flow-greeting-tts", daemon=True)
        thread.start()
        try:
            self.display.show_wake_success(wake_word)
        finally:
            thread.join()

        if errors:
            raise errors[0]


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
            wake_words = _display_wake_words(self.config)
            greeting_text = str(self.config.get("greeting.text", "小朋友你好"))

            self.display.show_status("正在准备唤醒监听...")
            event = self.wakeword.wait_for_wake(on_ready=lambda: self.display.show_standby(wake_words))
            self._speak_during_wake_animation(event.wake_word, greeting_text)
            self.display.show_greeting_complete()
        except RobotError as exc:
            self._logger.warning("唤醒问候流程发生可恢复错误：%s", exc)
            self.display.show_error(str(exc))
            time.sleep(float(self.config.get("app.max_error_pause_seconds", 5)))
        except Exception:
            self._logger.exception("唤醒问候流程发生未知错误。")
            self.display.show_error("问候流程遇到未知错误，正在返回待机。")
            time.sleep(float(self.config.get("app.max_error_pause_seconds", 5)))

    def _speak_during_wake_animation(self, wake_word: str, greeting_text: str) -> None:
        errors: list[Exception] = []

        def speak_greeting() -> None:
            try:
                self._logger.info("播放问候语：%s", greeting_text)
                self.tts.speak(greeting_text)
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=speak_greeting, name="wake-greeting-tts", daemon=True)
        thread.start()
        try:
            self.display.show_wake_success(wake_word)
        finally:
            thread.join()

        if errors:
            raise errors[0]


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
        speech_activity=_build_speech_activity(config),
        greeting_tts=_build_greeting_tts(config, audio_player),
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
        tts=_build_greeting_tts(config, audio_player),
    )


def run_wakeword_test(config_path: Path) -> None:
    """Run wake word detection without building API-backed modules."""
    config = load_config(config_path)
    setup_logging(config)
    display = _build_display(config)
    wakeword_engine = str(config.get("wakeword.engine", "console")).lower()
    speech_to_text = _build_speech_to_text(config) if wakeword_engine == "stt" else None
    wakeword = _build_wakeword(config, speech_to_text)

    wake_words = _display_wake_words(config)
    display.show_status("正在准备唤醒监听...")
    event = wakeword.wait_for_wake(on_ready=lambda: display.show_standby(wake_words))
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
    if engine in {"openwakeword", "oww"}:
        from modules.wakeword.openwakeword_wakeword import OpenWakeWordDetector

        return OpenWakeWordDetector(config)
    raise ConfigurationError(f"暂不支持的唤醒词引擎：{engine}")


def _build_recorder(config: AppConfig) -> AudioRecorder:
    engine = str(config.get("recording.engine", "sounddevice")).lower()
    if engine == "sounddevice":
        return SoundDeviceRecorder(config)
    raise ConfigurationError(f"暂不支持的录音引擎：{engine}")


def _build_speech_activity(config: AppConfig) -> SpeechActivityDetector | None:
    if not bool(config.get("post_wake_speech.enabled", True)):
        return None
    return SpeechActivityDetector(config)


def _build_speech_to_text(config: AppConfig) -> SpeechToTextProvider:
    provider = str(config.get("speech_to_text.provider", "openai")).lower()
    if provider == "openai":
        return OpenAISpeechToText(config)
    if provider in {"vosk", "local_vosk", "offline_vosk"}:
        return VoskSpeechToText(config)
    if provider in {"static", "offline_stub"}:
        return StaticSpeechToText(config)
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
    if provider == "piper":
        return PiperTextToSpeech(config, audio_player)
    if provider == "local_command":
        return LocalCommandTextToSpeech(config, audio_player)
    if provider == "local_audio":
        return LocalAudioTextToSpeech(config, audio_player)
    raise ConfigurationError(f"暂不支持的 TTS 供应商：{provider}")


def _build_greeting_tts(config: AppConfig, audio_player: AudioPlayer) -> TextToSpeechProvider:
    if bool(config.get("greeting.use_prerecorded_audio", False)):
        return LocalAudioTextToSpeech(config, audio_player)
    return _build_tts(config, audio_player)


def _build_display(config: AppConfig) -> Display:
    engine = str(config.get("display.engine", "console")).lower()
    if engine == "console":
        return ConsoleDisplay(config)
    if engine == "tkinter":
        return TkinterDisplay(config)
    if engine in {"robot_animation", "robot"}:
        return RobotAnimationDisplay(config)
    raise ConfigurationError(f"暂不支持的显示引擎：{engine}")


def _format_tts_text(user_text: str, reason: str, suggestion: str) -> str:
    quoted_text = _sanitize_tts_quote(user_text)
    cleaned_reason = reason.strip().rstrip("。！？!?,，")
    cleaned_suggestion = suggestion.strip().rstrip("。！？!?,，")
    return (
        f"小朋友，你刚才说的“{quoted_text}”，存在{cleaned_reason}的问题。"
        f"我觉得可以换一种表达方式：{cleaned_suggestion}"
    )


def _sanitize_tts_quote(text: str) -> str:
    cleaned = " ".join(str(text).split())
    cleaned = cleaned.replace("“", '"').replace("”", '"')
    cleaned = cleaned.replace('"', "")
    return cleaned or "刚才那句话"


def _display_wake_words(config: AppConfig) -> list[str]:
    display_wake_word = config.get("wakeword.display_wake_word", None)
    if display_wake_word:
        return [str(display_wake_word)]
    return list(config.get("wakeword.wake_words", []))


def _should_remind(analysis, config: AppConfig) -> bool:
    if not bool(config.get("analysis.remind_only_on_uncivilized", True)):
        return True

    remind_below_score = int(config.get("analysis.remind_below_score", 85))
    if analysis.score < remind_below_score:
        return True

    return not analysis.civilized
