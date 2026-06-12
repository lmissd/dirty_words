"""Text-to-speech interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TextToSpeechProvider(ABC):
    """Interface for TTS providers."""

    @abstractmethod
    def speak(self, text: str) -> Path | None:
        """Generate and optionally play speech audio."""
