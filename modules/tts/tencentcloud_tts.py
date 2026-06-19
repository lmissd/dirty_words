"""Tencent Cloud TTS adapter."""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from pathlib import Path

from modules.tts.base import TextToSpeechProvider
from modules.utils.audio_player import AudioPlayer
from modules.utils.config_loader import AppConfig
from modules.utils.disk import ensure_free_space
from modules.utils.errors import ApiError, ConfigurationError

LOGGER = logging.getLogger(__name__)
_DEFAULT_GREETING_TEXT = "小朋友你好"


class TencentCloudTextToSpeech(TextToSpeechProvider):
    """Generate speech with Tencent Cloud TTS and play it locally."""

    def __init__(self, config: AppConfig, audio_player: AudioPlayer) -> None:
        self.config = config
        self.audio_player = audio_player
        self.secret_id = self._require_env_with_fallback("tencentcloud_tts.secret_id_env", "tencentcloud.secret_id_env")
        self.secret_key = self._require_env_with_fallback(
            "tencentcloud_tts.secret_key_env",
            "tencentcloud.secret_key_env",
        )
        self.region = str(
            config.get(
                "tencentcloud_tts.region",
                config.get("tencentcloud.region", "ap-shanghai"),
            )
        )

    def speak(self, text: str) -> Path | None:
        """Generate cloud TTS audio and play it if enabled."""
        if not bool(self.config.get("tts.enabled", True)):
            LOGGER.info("腾讯云 TTS 已禁用，跳过语音生成。")
            return None

        spoken_text = self._prepare_text(text)
        output_path = self._resolve_output_path(text)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_free_space(output_path.parent)

        try:
            client, request = self._build_sdk_objects()
            request.from_json_string(
                json.dumps(
                    {
                        "Text": spoken_text,
                        "SessionId": output_path.stem,
                        "Volume": float(self.config.get("tts.volume", 0.0)),
                        "Speed": float(self.config.get("tts.speed", 0.0)),
                        "ProjectId": int(self.config.get("tts.project_id", 0)),
                        "ModelType": int(self.config.get("tts.model_type", 1)),
                        "VoiceType": int(self.config.get("tts.voice_type", 101001)),
                        "PrimaryLanguage": int(self.config.get("tts.primary_language", 1)),
                        "SampleRate": int(self.config.get("tts.sample_rate", 24000)),
                        "Codec": str(self.config.get("tts.codec", "wav")),
                        "EnableSubtitle": bool(self.config.get("tts.enable_subtitle", False)),
                        "SegmentRate": int(self.config.get("tts.segment_rate", 0)),
                        **self._build_emotion_payload(),
                    },
                    ensure_ascii=False,
                )
            )
            response = client.TextToVoice(request)
            payload = response.to_json_string()
            data = json.loads(payload)
            audio_base64 = str(data.get("Audio", "")).strip()
            if not audio_base64:
                LOGGER.warning("腾讯云 TTS 返回为空：%s", payload)
                raise ApiError("腾讯云 TTS 返回空音频。")

            output_path.write_bytes(base64.b64decode(audio_base64))
            LOGGER.info("腾讯云 TTS 生成完成：%s", output_path)
            self.audio_player.play(output_path)
            return output_path
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError(f"腾讯云 TTS 调用失败：{exc}") from exc

    def _build_sdk_objects(self):
        try:
            from tencentcloud.common import credential
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.tts.v20190823 import models, tts_client
        except ImportError as exc:
            raise ConfigurationError(
                "缺少腾讯云 TTS 依赖，请先执行 pip install -r requirements.txt"
            ) from exc

        cred = credential.Credential(self.secret_id, self.secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = "tts.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client = tts_client.TtsClient(cred, self.region, client_profile)
        request = models.TextToVoiceRequest()
        return client, request

    def _resolve_output_path(self, text: str) -> Path:
        greeting_text = str(self.config.get("greeting.text", _DEFAULT_GREETING_TEXT))
        codec = str(self.config.get("tts.codec", "wav")).lower()

        if text == greeting_text:
            greeting_path = Path(str(self.config.get("greeting.audio_path", "assets/audio/greeting.wav")))
            return greeting_path.with_suffix(f".{codec}")

        configured = self.config.get("tts.output_path", None)
        if configured:
            return Path(str(configured))

        output_dir = Path(str(self.config.get("paths.tts_output_dir", "recordings")))
        filename = datetime.now().strftime(f"tencentcloud_tts_%Y%m%d_%H%M%S.{codec}")
        return output_dir / filename

    def _prepare_text(self, text: str) -> str:
        greeting_text = str(self.config.get("greeting.text", _DEFAULT_GREETING_TEXT))
        if text == greeting_text:
            return str(self.config.get("greeting.tts_text", text)).strip()
        return str(text).strip()

    def _build_emotion_payload(self) -> dict[str, object]:
        emotion_category = str(self.config.get("tts.emotion_category", "")).strip()
        if not emotion_category:
            return {}
        return {
            "EmotionCategory": emotion_category,
            "EmotionIntensity": int(self.config.get("tts.emotion_intensity", 100)),
        }

    def _require_env_with_fallback(self, primary_key: str, fallback_key: str) -> str:
        if str(self.config.get(primary_key, "")).strip():
            return self.config.require_env(primary_key)
        return self.config.require_env(fallback_key)
