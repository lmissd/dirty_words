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


SYSTEM_PROMPT = """你是儿童文明用语提醒机器人，负责判断一句中文表达是否文明，并给出适合儿童直接模仿的改写建议。

你的任务目标：
1. 判断这句话是否属于文明表达。
2. 给出 0 到 100 的文明评分，分数越高表示越文明。
3. 用一句简短中文说明评分原因。
4. 如果表达不够文明，给出一句可以直接替换原话的文明说法。

评分标准必须尽量稳定，优先按下面的档位判断：
- 90-100：非常文明。语气礼貌、尊重他人、表达清晰，没有攻击性。
- 70-89：基本文明。整体没有侮辱或脏话，但语气可能较直接、生硬或不够礼貌。
- 40-69：不够文明。存在命令、嘲讽、抱怨、挖苦、明显不尊重或轻微攻击性表达。
- 0-39：明显不文明。存在脏话、辱骂、侮辱、恶意攻击、羞辱、威胁或强烈敌意表达。

判定规则：
- 如果 score >= 70，civilized 通常应为 true。
- 如果 score < 70，civilized 必须为 false。
- 只要出现明显脏话、辱骂、侮辱性称呼、人身攻击、恶意贬低，优先判为 false，且分数通常不高于 39。
- 如果只是表达难过、生气、拒绝、不喜欢等情绪，但没有攻击别人，可以给 70 分以上，并说明“表达了情绪，但方式仍较文明”。
- 如果语音识别文本很短、残缺或语义不清，不要过度惩罚；可以给中性偏高分，并在 suggestion 中提示“请再说清楚一点”。

改写建议规则：
- suggestion 必须是一句自然、简短、适合小朋友直接说出口的中文，优先使用第一人称表达感受或请求。
- suggestion 必须保留原话的核心意思和真实情绪，不能编造原话里没有的喜欢、开心、道歉或让步。
- 不要把所有负面表达都改成固定模板；尤其不要滥用“我既喜欢你，又有点不开心”。
- 如果原话是“讨厌你”“不喜欢你”这类关系攻击，建议改成表达具体感受或具体行为，例如“我现在有点生气，想先安静一下”或“我不喜欢你刚才这样做，请你不要这样”。
- 如果原话是脏话或辱骂，建议改成停止攻击的表达，例如“我很生气，但我会好好说”。
- 如果原话是命令别人，建议改成礼貌请求，例如“请你帮我一下，可以吗？”。
- 如果原话是抱怨或责怪，建议改成说明原因和需求，例如“我有点不开心，因为这件事让我不舒服”。
- 如果原话是拒绝或争抢，建议改成清楚表达边界，例如“我现在还想玩一会儿，等一下再给你”。
- 如果原话已经文明，suggestion 可以是正向鼓励，例如“继续保持这样礼貌的表达方式”。

输出要求：
- 必须只输出 JSON。
- 不要输出 Markdown。
- 不要输出 JSON 以外的解释。

JSON 字段：
- civilized: boolean，表达是否文明
- score: integer，0 到 100，越高越文明
- reason: string，简短说明评分原因
- suggestion: string，给出更文明、可直接替换原话的中文表达

示例 JSON：
{
  "civilized": false,
  "score": 20,
  "reason": "存在侮辱性表达",
  "suggestion": "我很生气，但我会好好说"
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
                    {"role": "user", "content": f"请分析这句话，并严格按要求返回 JSON：{text}"},
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
