"""Copy selected repo files to the Raspberry Pi over SFTP."""

from __future__ import annotations

from pathlib import Path
import posixpath

import paramiko

HOST = "192.168.1.3"
PORT = 22
USERNAME = "pi"
PASSWORD = "20010929"
REMOTE_ROOT = "/home/pi/dirty_words"

FILES = [
    ".gitignore",
    "PROJECT_MEMORY.md",
    "README.md",
    "config/config.example.yaml",
    "config/raspberry-pi.example.yaml",
    "docs/ARCHITECTURE.md",
    "docs/DEPLOYMENT_RASPBERRY_PI.md",
    "docs/OFFLINE_WAKEWORD.md",
    "docs/VOICE_WAKEWORD.md",
    "modules/app.py",
    "modules/recorder/sounddevice_recorder.py",
    "modules/tts/piper_tts.py",
    "modules/wakeword/openwakeword_wakeword.py",
    "requirements.txt",
    "scripts/collect_negative_samples.py",
    "scripts/collect_wakeword_samples.py",
    "scripts/download_openwakeword_resources.py",
    "scripts/export_wakeword_training_bundle.py",
    "scripts/install_openwakeword_pi.py",
    "scripts/train_fantuan_wakeword_model.py",
    "scripts/list_audio_devices.py",
    "scripts/play_wake_animation.py",
    "scripts/review_positive_samples.py",
    "tests/test_collect_negative_samples.py",
    "tests/test_collect_wakeword_samples.py",
    "tests/test_export_wakeword_training_bundle.py",
    "tests/test_openwakeword_wakeword.py",
    "tests/test_piper_tts.py",
    "tests/test_review_positive_samples.py",
    "tests/test_sounddevice_recorder.py",
]


def main() -> None:
    """Upload all selected files to the Raspberry Pi."""
    repo_root = Path(__file__).resolve().parents[1]

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=10)

    try:
        sftp = client.open_sftp()
        try:
            for relative_path in FILES:
                local_path = repo_root / relative_path
                remote_path = posixpath.join(REMOTE_ROOT, relative_path.replace("\\", "/"))
                ensure_remote_parent_dirs(sftp, posixpath.dirname(remote_path))
                sftp.put(str(local_path), remote_path)
                print(f"uploaded {relative_path}")
        finally:
            sftp.close()
    finally:
        client.close()


def ensure_remote_parent_dirs(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    """Create remote parent directories recursively if they do not exist."""
    if not remote_dir or remote_dir == "/":
        return

    parts = remote_dir.strip("/").split("/")
    current = ""
    for part in parts:
        current = f"{current}/{part}"
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


if __name__ == "__main__":
    main()
