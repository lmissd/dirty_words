"""Install openWakeWord on Raspberry Pi Python 3.12+ without tflite-runtime."""

from __future__ import annotations

import platform
import subprocess
import sys


def main() -> None:
    """Install the ONNX-only openWakeWord stack for Raspberry Pi."""
    if platform.system() != "Linux" or platform.machine() != "aarch64":
        print("当前环境不是 Raspberry Pi Linux aarch64，跳过专用安装。")
        return

    python_version = sys.version_info
    if python_version < (3, 12):
        print("当前 Python 版本低于 3.12，可直接使用 pip install -r requirements.txt。")
        return

    _run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "onnxruntime>=1.10.0,<2",
            "scipy>=1.3,<2",
            "scikit-learn>=1,<2",
            "requests>=2.0",
            "tqdm>=4.0",
            "speexdsp-ns>=0.1.2",
        ]
    )
    _run([sys.executable, "-m", "pip", "install", "--no-deps", "openwakeword==0.6.0"])
    _run([sys.executable, "scripts/download_openwakeword_resources.py"])


def _run(command: list[str]) -> None:
    print(f"Running: {' '.join(command)}")
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
