"""List PortAudio devices visible to Python sounddevice."""

from __future__ import annotations

import sounddevice as sd


def main() -> None:
    """Print audio devices and their input/output channel counts."""
    print(sd.query_devices())


if __name__ == "__main__":
    main()
