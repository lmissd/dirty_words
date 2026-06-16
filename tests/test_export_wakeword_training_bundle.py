"""Tests for wake word training bundle export helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.export_wakeword_training_bundle import copy_wavs, write_csv_snapshot


class ExportWakewordTrainingBundleTests(unittest.TestCase):
    def test_copy_wavs_copies_nested_wavs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            target_dir = Path(temp_dir) / "target"
            (source_dir / "a").mkdir(parents=True)
            (source_dir / "a" / "one.wav").write_bytes(b"one")
            (source_dir / "b").mkdir(parents=True)
            (source_dir / "b" / "two.wav").write_bytes(b"two")
            (source_dir / "b" / "skip.txt").write_text("x", encoding="utf-8")

            copied = copy_wavs(source_dir, target_dir)

            self.assertEqual(copied, 2)
            self.assertTrue((target_dir / "one.wav").exists())
            self.assertTrue((target_dir / "two.wav").exists())

    def test_write_csv_snapshot_creates_placeholder_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "metadata.csv"

            write_csv_snapshot(Path(temp_dir) / "missing.csv", target)

            self.assertEqual(target.read_text(encoding="utf-8").strip(), "file")

    def test_write_csv_snapshot_copies_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.csv"
            target = Path(temp_dir) / "target.csv"
            source.write_text("file\nsample.wav\n", encoding="utf-8")

            write_csv_snapshot(source, target)

            self.assertEqual(target.read_text(encoding="utf-8"), "file\nsample.wav\n")


if __name__ == "__main__":
    unittest.main()
