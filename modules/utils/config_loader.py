"""Configuration loading and typed access helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from modules.utils.errors import ConfigurationError

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional until dependencies are installed.
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False

try:
    import yaml
except ImportError:  # pragma: no cover - reported at runtime with a clear message.
    yaml = None


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Thin wrapper around the YAML configuration."""

    data: dict[str, Any]
    path: Path

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Read a nested value using dot notation."""
        current: Any = self.data
        for part in dotted_key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def require_env(self, dotted_key: str) -> str:
        """Resolve an environment variable name stored in config."""
        env_name = str(self.get(dotted_key, "")).strip()
        if not env_name:
            raise ConfigurationError(f"缺少环境变量配置项：{dotted_key}")

        value = os.getenv(env_name)
        if not value or value.startswith("replace-with-"):
            raise ConfigurationError(f"缺少环境变量：{env_name}")
        return value


def load_config(config_path: Path) -> AppConfig:
    """Load config YAML and .env values."""
    load_dotenv()

    if yaml is None:
        raise ConfigurationError("缺少 PyYAML，请先执行 pip install -r requirements.txt")

    if not config_path.exists():
        example_path = Path("config/config.example.yaml")
        raise ConfigurationError(
            f"配置文件不存在：{config_path}。请复制 {example_path} 为 config/config.yaml。"
        )

    try:
        with config_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
    except OSError as exc:
        raise ConfigurationError(f"读取配置失败：{exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"解析配置 YAML 失败：{exc}") from exc

    if not isinstance(data, dict):
        raise ConfigurationError("配置文件根节点必须是对象。")
    return AppConfig(data=data, path=config_path)
