"""Tests for wake word sample collection helpers."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.collect_wakeword_samples import RecordingPlan, append_metadata, next_sample_index


class CollectWakewordSamplesTests(unittest.TestCase):
    def test_next_sample_index_continues_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "fantuan_fantuan_0001.wav").write_bytes(b"fake")
            (output_dir / "fantuan_fantuan_0007.wav").write_bytes(b"fake")
            (output_dir / "other.wav").write_bytes(b"fake")

            self.assertEqual(next_sample_index(output_dir), 8)

    def test_append_metadata_writes_expected_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            metadata_path = output_dir / "metadata.csv"
            plan = RecordingPlan(
                phrase="饭团饭团",
                output_dir=output_dir,
                duration_seconds=2.0,
                sample_rate=48000,
                channels=1,
                count=1,
                start_index=1,
                device=1,
            )

            append_metadata(metadata_path, output_dir / "fantuan_fantuan_0001.wav", plan)

            with metadata_path.open("r", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["file"], "fantuan_fantuan_0001.wav")
        self.assertEqual(rows[0]["phrase"], "饭团饭团")
        self.assertEqual(rows[0]["sample_rate"], "48000")
        self.assertEqual(rows[0]["channels"], "1")
        self.assertEqual(rows[0]["duration_seconds"], "2.000")


if __name__ == "__main__":
    unittest.main()
