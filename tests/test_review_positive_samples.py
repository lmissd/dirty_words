"""Tests for positive sample review helpers."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.review_positive_samples import (
    append_negative_metadata,
    move_to_negative,
    rebuild_positive_metadata,
)


class ReviewPositiveSamplesTests(unittest.TestCase):
    def test_move_to_negative_renames_into_review_noise_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            positive = root / "positive"
            negative = root / "negative" / "review_noise"
            positive.mkdir(parents=True)
            negative.mkdir(parents=True)
            sample = positive / "fantuan_fantuan_0003.wav"
            sample.write_bytes(b"fake")

            target = move_to_negative(sample, negative)

            self.assertFalse(sample.exists())
            self.assertTrue(target.exists())
            self.assertIn("review_noise_", target.name)

    def test_rebuild_positive_metadata_matches_remaining_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            positive = Path(temp_dir)
            (positive / "fantuan_fantuan_0001.wav").write_bytes(b"fake")
            (positive / "fantuan_fantuan_0002.wav").write_bytes(b"fake")

            rebuild_positive_metadata(positive)

            with (positive / "metadata.csv").open("r", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual([row["file"] for row in rows], ["fantuan_fantuan_0001.wav", "fantuan_fantuan_0002.wav"])

    def test_append_negative_metadata_adds_review_noise_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            negative_parent = Path(temp_dir) / "negative"
            review_dir = negative_parent / "review_noise"
            review_dir.mkdir(parents=True)
            sample = review_dir / "review_noise_0001.wav"
            sample.write_bytes(b"fake")

            append_negative_metadata(review_dir, sample)

            with (negative_parent / "metadata.csv").open("r", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], "review_noise")
        self.assertEqual(rows[0]["file"], "review_noise/review_noise_0001.wav")


if __name__ == "__main__":
    unittest.main()
