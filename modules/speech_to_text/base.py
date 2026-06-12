"""Speech-to-text interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class SpeechToTextProvider(ABC):
    """Interface for speech recognition providers."""

    @abstractmethod
    def transcribe(self, audio_path: Path) -> str:
        """Transcribe a local audio file to text."""
