"""OpenAI client construction."""

from __future__ import annotations

from modules.utils.config_loader import AppConfig
from modules.utils.openai_compatible_client import build_openai_compatible_client


def build_openai_client(config: AppConfig):
    """Build an OpenAI client from environment-managed credentials."""
    return build_openai_compatible_client(config, "openai")
