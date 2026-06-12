"""Tests for civility analysis parsing."""

from __future__ import annotations

import unittest

from modules.llm.openai_civil_analyzer import parse_analysis_json
from modules.utils.errors import JsonParseError


class AnalysisParserTests(unittest.TestCase):
    def test_parse_valid_json(self) -> None:
        analysis = parse_analysis_json(
            '{"civilized": false, "score": 20, "reason": "存在侮辱性表达", "suggestion": "请换一种更尊重的说法"}'
        )

        self.assertFalse(analysis.civilized)
        self.assertEqual(analysis.score, 20)
        self.assertEqual(analysis.reason, "存在侮辱性表达")

    def test_parse_json_fence(self) -> None:
        analysis = parse_analysis_json(
            """```json
{"civilized": true, "score": 95, "reason": "表达礼貌", "suggestion": "继续保持"}
```"""
        )

        self.assertTrue(analysis.civilized)
        self.assertEqual(analysis.score, 95)

    def test_missing_field_raises(self) -> None:
        with self.assertRaises(JsonParseError):
            parse_analysis_json('{"civilized": true, "score": 90}')


if __name__ == "__main__":
    unittest.main()
