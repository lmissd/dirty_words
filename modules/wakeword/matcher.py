"""Wake phrase matching helpers."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from modules.utils.config_loader import AppConfig


@dataclass(frozen=True, slots=True)
class WakeMatcherConfig:
    """Config for exact, alias, and fuzzy wake matching."""

    display_wake_word: str
    wake_phrases: list[str]
    strict_match: bool
    wake_aliases: list[str]
    fuzzy_enabled: bool
    fuzzy_threshold: float
    require_greeting: bool
    greeting_words: list[str]
    subject_keywords: list[str]

    @classmethod
    def from_app_config(cls, config: AppConfig) -> "WakeMatcherConfig":
        """Build matcher config from YAML config."""
        wake_phrases = _string_list(config.get("wakeword.wake_words", ["范小团你好"]))
        display = str(config.get("wakeword.display_wake_word", wake_phrases[0]))
        return cls(
            display_wake_word=display,
            wake_phrases=wake_phrases,
            strict_match=bool(config.get("wakeword.strict_match", False)),
            wake_aliases=_string_list(config.get("wakeword.wake_aliases", [])),
            fuzzy_enabled=bool(config.get("wakeword.fuzzy_enabled", True)),
            fuzzy_threshold=float(config.get("wakeword.fuzzy_threshold", 0.62)),
            require_greeting=bool(config.get("wakeword.require_greeting", True)),
            greeting_words=_string_list(config.get("wakeword.greeting_words", ["你好", "你号"])),
            subject_keywords=_string_list(config.get("wakeword.subject_keywords", ["小团"])),
        )


def match_wake_phrase(text: str, config: WakeMatcherConfig) -> str | None:
    """Return the display wake phrase when the transcript should trigger wake."""
    normalized_text = normalize_text(text)
    if not normalized_text:
        return None

    for phrase in config.wake_phrases:
        normalized_phrase = normalize_text(phrase)
        if normalized_phrase and normalized_phrase in normalized_text:
            return config.display_wake_word

    if config.strict_match:
        return None

    for phrase in config.wake_aliases:
        normalized_phrase = normalize_text(phrase)
        if normalized_phrase and normalized_phrase in normalized_text:
            return config.display_wake_word

    if not config.fuzzy_enabled:
        return None

    has_greeting = any(normalize_text(word) in normalized_text for word in config.greeting_words)
    if config.require_greeting and not has_greeting:
        return None

    has_subject = any(normalize_text(word) in normalized_text for word in config.subject_keywords)
    if has_subject and has_greeting:
        return config.display_wake_word

    target = normalize_text(config.display_wake_word)
    if similarity(normalized_text, target) >= config.fuzzy_threshold:
        return config.display_wake_word

    return None


def similarity(left: str, right: str) -> float:
    """Return a stable similarity score between normalized phrases."""
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def normalize_text(text: str) -> str:
    """Normalize text so Chinese wake words survive punctuation and spaces."""
    ignored = set(" \t\r\n，。！？!?、,.；;：:\"'“”‘’（）()[]{}<>《》")
    return "".join(char.lower() for char in text if char not in ignored)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]
