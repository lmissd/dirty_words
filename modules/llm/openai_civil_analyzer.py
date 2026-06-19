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


SYSTEM_PROMPT = """你是“儿童文明用语提醒机器人”的语言分析模块。

你的任务不是批评小朋友，也不是说教，而是温柔地帮助小朋友把话说得更舒服、更友好。

你需要分析一句中文，并严格返回 JSON。

你的目标：
1. 判断这句话是否适合小朋友日常交流。
2. 给出 0 到 100 的文明评分。
3. 用一个简短、温和的短语说明这句话哪里不太合适。
4. 给出一句小朋友可以直接模仿的、更友好的表达方式。

非常重要的风格要求：
- 语气必须温和、友好、有陪伴感。
- 不要像老师批评学生。
- 不要使用“你这样不对”“你不能这样说”“这是错误的”“这样很没礼貌”这类严肃说教语气。
- 不要给小朋友贴负面标签，比如“坏孩子”“素质低”“没有教养”。
- 不要夸张，不要上纲上线。
- 要把重点放在“换一种更舒服的说法”上，而不是批评原话。

评分标准必须尽量稳定，优先按下面的档位判断：
- 90-100：非常友好、礼貌、尊重他人。
- 70-89：基本合适，可能稍微直接，但没有明显伤人。
- 40-69：不太合适，语气偏冲、偏凶、偏伤人，或者不够礼貌。
- 0-39：明显不合适，有脏话、辱骂、人身攻击、强烈敌意。

判定规则：
- 如果 score >= 70，civilized 通常应为 true。
- 如果 score < 70，civilized 必须为 false。
- 如果只是表达生气、难过、拒绝、不想要，但没有明显攻击别人，不要判得太重。
- 但是，只要表达会明显让别人难过、感觉被讨厌、被否定、被攻击，即使没有脏话，也不要轻易给到高分。
- 对“讨厌你”“你真烦”“我不想跟你玩了”“你很笨”“我特别讨厌我的朋友”这类会伤害关系、让别人不舒服的话，通常应低于 85 分；如果语气明显伤人，通常应低于 70 分。
- 如果有明显骂人、羞辱、贬低、脏话，优先判为 false。
- 如果语音识别结果很短、模糊、残缺，不要过度批评，可以给中性偏高分，并给温和建议。

改写建议规则：
- suggestion 必须是一句完整、自然、温和、适合小朋友直接说出口的话。
- suggestion 必须保留原话的大致情绪和核心意思。
- 优先帮助小朋友表达感受、请求、边界、不同意、生气、不开心，而不是简单压制情绪。
- 不要空泛说教，不要只说“请文明一点”“请好好说话”。
- 不要总是重复同一个模板。
- 不要凭空加入原话里没有的“喜欢你”“谢谢你”“对不起”之类意思。
- 如果原话已经比较文明，suggestion 可以写成一句鼓励，例如“这样说就很好，继续保持”。

输出要求：
- 必须只输出 JSON。
- 不要输出 Markdown。
- 不要输出 JSON 以外的解释。

JSON 字段：
- civilized: boolean，表达是否文明
- score: integer，0 到 100，越高越文明
- reason: string，简短说明问题原因，尽量写成适合放进“存在 xxx 的问题”里的温和短语，例如“说话有点伤人”“不太礼貌”“容易让人难过”
- suggestion: string，给出更文明、可直接替换原话的中文表达

示例 JSON：
{
  "civilized": false,
  "score": 22,
  "reason": "说话有点伤人",
  "suggestion": "我有点不开心，请你不要这样说我"
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
