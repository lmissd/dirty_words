"""OpenAI GPT-powered civil language analyzer."""

from __future__ import annotations

import json
import logging
from typing import Any

from modules.llm.base import CivilLanguageAnalyzer
from modules.models import CivilityAnalysis
from modules.utils.config_loader import AppConfig
from modules.utils.errors import ApiError, JsonParseError
from modules.utils.openai_client import build_openai_client

LOGGER = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是儿童文明用语提醒机器人。
请判断用户的话是否文明，并给出温和、积极、适合儿童理解的改写建议。
必须只输出 JSON，不要输出 Markdown，不要解释 JSON 以外的内容。
JSON 字段：
- civilized: boolean，表达是否文明
- score: integer，0 到 100，越高越文明
- reason: string，简短说明问题原因或表扬原因
- suggestion: string，给出更文明的中文表达建议
示例 JSON：
{
  "civilized": false,
  "score": 20,
  "reason": "存在侮辱性表达",
  "suggestion": "请尝试使用更加尊重对方的表达方式"
}
"""


class OpenAICivilLanguageAnalyzer(CivilLanguageAnalyzer):
    """Analyze civility with OpenAI Chat Completions JSON mode."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = build_openai_client(config)

    def analyze(self, text: str) -> CivilityAnalysis:
        """Analyze text and parse the model JSON response."""
        model = str(self.config.get("llm.model", "gpt-4o-mini"))
        temperature = float(self.config.get("llm.temperature", 0.2))
        max_tokens = int(self.config.get("llm.max_tokens", 500))

        try:
            response = self.client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"请分析这句话：{text}"},
                ],
            )
            content = response.choices[0].message.content or "{}"
            analysis = parse_analysis_json(content)
            LOGGER.info(
                "文明分析完成：civilized=%s score=%s reason=%s",
                analysis.civilized,
                analysis.score,
                analysis.reason,
            )
            return analysis
        except JsonParseError:
            raise
        except Exception as exc:
            raise ApiError(f"文明分析 API 调用失败：{exc}") from exc


def parse_analysis_json(content: str) -> CivilityAnalysis:
    """Parse and validate LLM JSON output."""
    cleaned = _strip_json_fences(content)
    try:
        data: Any = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise JsonParseError(f"文明分析 JSON 解析失败：{exc}") from exc

    if not isinstance(data, dict):
        raise JsonParseError("文明分析 JSON 根节点必须是对象。")

    missing = {"civilized", "score", "reason", "suggestion"} - set(data)
    if missing:
        raise JsonParseError(f"文明分析 JSON 缺少字段：{', '.join(sorted(missing))}")

    return CivilityAnalysis.from_dict(data)


def _strip_json_fences(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text
