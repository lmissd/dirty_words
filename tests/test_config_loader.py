"""Tests for config access helpers."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from modules.utils.config_loader import AppConfig
from modules.utils.errors import ConfigurationError


class ConfigLoaderTests(unittest.TestCase):
    def test_get_nested_key(self) -> None:
        config = AppConfig(data={"a": {"b": 3}}, path=Path("config/config.example.yaml"))

        self.assertEqual(config.get("a.b"), 3)
        self.assertEqual(config.get("a.c", "default"), "default")

    def test_require_env(self) -> None:
        config = AppConfig(data={"openai": {"api_key_env": "TEST_ROBOT_KEY"}}, path=Path("x"))
        os.environ["TEST_ROBOT_KEY"] = "secret"
        try:
            self.assertEqual(config.require_env("openai.api_key_env"), "secret")
        finally:
            os.environ.pop("TEST_ROBOT_KEY", None)

    def test_require_env_missing_raises(self) -> None:
        config = AppConfig(data={"openai": {"api_key_env": "MISSING_ROBOT_KEY"}}, path=Path("x"))

        with self.assertRaises(ConfigurationError):
            config.require_env("openai.api_key_env")


if __name__ == "__main__":
    unittest.main()
