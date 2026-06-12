"""OpenAI client construction."""

from __future__ import annotations

from modules.utils.config_loader import AppConfig
from modules.utils.errors import ConfigurationError


def build_openai_client(config: AppConfig):
    """Build an OpenAI client from environment-managed credentials."""
    api_key = config.require_env("openai.api_key_env")
    timeout_seconds = float(config.get("openai.timeout_seconds", 30))
    max_retries = int(config.get("openai.max_retries", 2))

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ConfigurationError("缺少 openai 依赖，请先执行 pip install -r requirements.txt") from exc

    return OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=max_retries)
