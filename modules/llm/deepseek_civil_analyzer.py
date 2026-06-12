"""DeepSeek-powered civil language analyzer."""

from __future__ import annotations

import logging

from modules.llm.base import CivilLanguageAnalyzer
from modules.llm.openai_civil_analyzer import SYSTEM_PROMPT, parse_analysis_json
from modules.models import CivilityAnalysis
from modules.utils.config_loader import AppConfig
from modules.utils.errors import ApiError, JsonParseError
from modules.utils.openai_compatible_client import build_openai_compatible_client

LOGGER = logging.getLogger(__name__)


class DeepSeekCivilLanguageAnalyzer(CivilLanguageAnalyzer):
    """Analyze civility with DeepSeek's OpenAI-compatible chat API."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = build_openai_compatible_client(config, "deepseek")

    def analyze(self, text: str) -> CivilityAnalysis:
        """Analyze text and parse the DeepSeek JSON response."""
        model = str(self.config.get("llm.model", "deepseek-v4-flash"))
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
                    {"role": "user", "content": f"请分析这句话，并返回 JSON：{text}"},
                ],
            )
            content = response.choices[0].message.content or "{}"
            analysis = parse_analysis_json(content)
            LOGGER.info(
                "DeepSeek 文明分析完成：civilized=%s score=%s reason=%s",
                analysis.civilized,
                analysis.score,
                analysis.reason,
            )
            return analysis
        except JsonParseError:
            raise
        except Exception as exc:
            raise ApiError(f"DeepSeek 文明分析 API 调用失败：{exc}") from exc
