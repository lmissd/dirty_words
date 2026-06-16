"""Tests for negative wake word sample collection helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.collect_negative_samples import build_prompt_plan, next_sample_index


class CollectNegativeSamplesTests(unittest.TestCase):
    def test_next_sample_index_continues_existing_category_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "near_miss_0002.wav").write_bytes(b"fake")
            (output_dir / "near_miss_0005.wav").write_bytes(b"fake")

            self.assertEqual(next_sample_index(output_dir, "near_miss"), 6)

    def test_mixed_prompt_plan_contains_all_categories(self) -> None:
        prompts = build_prompt_plan("mixed", "饭团饭团")
        categories = {item.category for item in prompts}

        self.assertEqual(categories, {"near_miss", "other_speech", "ambient"})
        self.assertGreaterEqual(len(prompts), 10)


if __name__ == "__main__":
    unittest.main()
