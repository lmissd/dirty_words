"""Tencent Cloud short-speech speech-to-text adapter."""

from __future__ import annotations

import base64
import json
import logging
import wave
from pathlib import Path

from modules.speech_to_text.base import SpeechToTextProvider
from modules.speech_to_text.vosk_stt import _load_audio
from modules.utils.config_loader import AppConfig
from modules.utils.errors import ApiError, ConfigurationError

LOGGER = logging.getLogger(__name__)


class TencentCloudSpeechToText(SpeechToTextProvider):
    """Transcribe short recorded audio with Tencent Cloud ASR."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.secret_id = config.require_env("tencentcloud.secret_id_env")
        self.secret_key = config.require_env("tencentcloud.secret_key_env")
        self.region = str(config.get("tencentcloud.region", "ap-shanghai"))
        self.engine_model_type = str(config.get("tencentcloud.engine_model_type", "16k_zh"))
        self.voice_format = str(config.get("tencentcloud.voice_format", "wav"))
        self.convert_num_mode = int(config.get("tencentcloud.convert_num_mode", 1))
        self.filter_dirty = int(config.get("tencentcloud.filter_dirty", 0))
        self.filter_modal = int(config.get("tencentcloud.filter_modal", 0))
        self.filter_punc = int(config.get("tencentcloud.filter_punc", 0))
        self.word_info = int(config.get("tencentcloud.word_info", 0))
        self.hotword_id = str(config.get("tencentcloud.hotword_id", "")).strip()
        self.hotword_list = str(config.get("tencentcloud.hotword_list", "")).strip()
        self.target_sample_rate = int(config.get("speech_to_text.sample_rate", 16000))

    def transcribe(self, audio_path: Path) -> str:
        """Transcribe a short WAV file using Tencent Cloud sentence recognition."""
        audio_bytes = _build_tencent_wav_bytes(audio_path, self.target_sample_rate)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        try:
            client, request = self._build_sdk_objects()
            request.from_json_string(
                json.dumps(
                    {
                        "EngSerViceType": self.engine_model_type,
                        "SourceType": 1,
                        "VoiceFormat": self.voice_format,
                        "UsrAudioKey": audio_path.stem,
                        "Data": audio_base64,
                        "DataLen": len(audio_bytes),
                        "ConvertNumMode": self.convert_num_mode,
                        "FilterDirty": self.filter_dirty,
                        "FilterModal": self.filter_modal,
                        "FilterPunc": self.filter_punc,
                        "WordInfo": self.word_info,
                        **self._build_hotword_payload(),
                    },
                    ensure_ascii=False,
                )
            )
            response = client.SentenceRecognition(request)
            payload = response.to_json_string()
            data = json.loads(payload)
            text = str(data.get("Result", "")).strip()
            if not text:
                LOGGER.warning("腾讯云语音识别返回为空：%s", payload)
                raise ApiError("腾讯云语音识别返回为空。")
            LOGGER.info("腾讯云语音识别完成：%s", text)
            return text
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError(f"腾讯云语音识别调用失败：{exc}") from exc

    def _build_sdk_objects(self):
        try:
            from tencentcloud.common import credential
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.asr.v20190614 import asr_client, models
        except ImportError as exc:
            raise ConfigurationError(
                "缺少腾讯云语音识别依赖，请先执行 pip install -r requirements.txt"
            ) from exc

        cred = credential.Credential(self.secret_id, self.secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = "asr.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client = asr_client.AsrClient(cred, self.region, client_profile)
        request = models.SentenceRecognitionRequest()
        return client, request

    def _build_hotword_payload(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        if self.hotword_id:
            payload["HotwordId"] = self.hotword_id
        if self.hotword_list:
            payload["HotwordList"] = self.hotword_list
        return payload


def _build_tencent_wav_bytes(audio_path: Path, target_sample_rate: int) -> bytes:
    """Load audio, normalize it to mono PCM16 WAV, and return file bytes."""
    try:
        import io
    except ImportError as exc:
        raise ConfigurationError("缺少 io 依赖，Python 运行环境异常。") from exc

    pcm16 = _load_audio(audio_path, target_sample_rate)
    if pcm16.size == 0:
        raise ApiError("录音文件为空，无法上传到腾讯云语音识别。")

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(target_sample_rate)
        wav_file.writeframes(pcm16.astype("<i2", copy=False).tobytes())
    return buffer.getvalue()
