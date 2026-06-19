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


@dataclass(slots=True)
class PcmAudioBuffer:
    """Raw PCM audio captured before the main recording starts."""

    data: bytes
    sample_rate: int
    channels: int
    sample_width_bytes: int = 2


class AudioRecorder(ABC):
    """Interface for audio recorders."""

    @abstractmethod
    def record(self, pre_roll_audio: PcmAudioBuffer | None = None) -> RecordedAudio:
        """Record audio and return the generated file path."""
