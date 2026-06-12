"""OpenAI-compatible client construction."""

from __future__ import annotations

from modules.utils.config_loader import AppConfig
from modules.utils.errors import ConfigurationError


def build_openai_compatible_client(config: AppConfig, section: str):
    """Build an OpenAI SDK client for OpenAI-compatible providers."""
    api_key = config.require_env(f"{section}.api_key_env")
    timeout_seconds = float(config.get(f"{section}.timeout_seconds", 30))
    max_retries = int(config.get(f"{section}.max_retries", 2))
    base_url = config.get(f"{section}.base_url", None)

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ConfigurationError("缺少 openai 依赖，请先执行 pip install -r requirements.txt") from exc

    kwargs = {
        "api_key": api_key,
        "timeout": timeout_seconds,
        "max_retries": max_retries,
    }
    if base_url:
        kwargs["base_url"] = str(base_url)
    return OpenAI(**kwargs)
