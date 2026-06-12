"""Custom exception hierarchy for recoverable robot errors."""

from __future__ import annotations


class RobotError(Exception):
    """Base class for errors that should not crash the process immediately."""


class ConfigurationError(RobotError):
    """Configuration is missing or invalid."""


class NetworkError(RobotError):
    """Network is unavailable or a remote service timed out."""


class ApiError(RobotError):
    """A remote API call failed."""


class AudioInputError(RobotError):
    """Microphone or recording failed."""


class AudioOutputError(RobotError):
    """Speaker, playback, or TTS output failed."""


class DisplayError(RobotError):
    """Screen rendering failed."""


class StorageError(RobotError):
    """Storage is unavailable or space is insufficient."""


class JsonParseError(RobotError):
    """The LLM response could not be parsed as valid JSON."""
