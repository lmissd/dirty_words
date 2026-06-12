"""Recording interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RecordedAudio:
    """Metadata for a recorded audio file."""

    path: Path
    duration_seconds: float
    sample_rate: int


class AudioRecorder(ABC):
    """Interface for audio recorders."""

    @abstractmethod
    def record(self) -> RecordedAudio:
        """Record audio and return the generated file path."""
