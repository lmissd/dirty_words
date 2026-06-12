"""Generate the offline greeting wav used by wake-greeting mode."""

from __future__ import annotations

import math
import wave
from pathlib import Path


OUTPUT_PATH = Path("assets/audio/greeting.wav")


def main() -> None:
    """Generate a simple offline chime placeholder for the greeting."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 48000
    duration_seconds = 0.9
    amplitude = 12000
    tones = [659.25, 783.99, 987.77]
    samples = []
    total_frames = int(sample_rate * duration_seconds)

    for frame in range(total_frames):
        time = frame / sample_rate
        tone = tones[min(int(time / (duration_seconds / len(tones))), len(tones) - 1)]
        envelope = min(1.0, frame / (sample_rate * 0.05), (total_frames - frame) / (sample_rate * 0.08))
        value = int(amplitude * envelope * math.sin(2 * math.pi * tone * time))
        samples.append(value)

    with wave.open(str(OUTPUT_PATH), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))

    print(f"Generated offline greeting audio: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
