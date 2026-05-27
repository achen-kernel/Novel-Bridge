"""@NB-ENTRYPOINT P3 PromptSelector — intent → prompt template.

Replaces the hardcoded answer/analyze/trace/enrich mode runners.
Intent comes from QueryRewriter, template is selected here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

IntentType = Literal["factual", "relation_analysis", "trace_timeline", "abstract_meaning", "enumeration"]


@dataclass
class PromptConfig:
    system_prompt: str
    template_name: str
    temperature: float = 0.3
    max_tokens: int = 2048


def select_prompt(intent: IntentType, book_title: str = "", target_name: str = "") -> PromptConfig:
    """Select prompt template based on intent from QueryRewriter.

    Each intent maps to a different system prompt.
    The caller (unified_pipeline) renders this with retrieved contexts.
    """
    _system_prompts = {
        "factual": f"""你是小说《{book_title}》的阅读理解助手。
请基于提供的参考段落来回答问题。每段前的方括号标记了来源类型。

信息来源优先级：
1. 原文段落（chunk）= 最直接证据
2. 角色档案（entity_profile）= 描述角色的标准信息
3. 角色关系（relation）= 关系事实
4. 事件记录（event）= 事件摘要

引用要求：
- 每个关键事实必须引用具体来源
- 引用格式：<cite type="chunk" id="编号">原文片段</cite>
- 对于枚举性问题，必须逐条引用每个条目

回答要求：
- 先直接回答问题，再补充必要分析
- 不要复述检索到的原文
- 关键事实应有引用
- 如果证据不足，明确说"基于现有证据无法确认"
- 不要编造不存在的内容""",

        "relation_analysis": f"""你是小说《{book_title}》的关系分析助手。
请基于提供的参考段落，分析人物之间的关系。

分析框架：
1. 综合判断：关系性质（师徒/敌对/合作/亲情等）
2. 关键证据：列出支持判断的具体原文引用
3. 冲突或合作：说明关系中的关键事件
4. 证据局限：如果证据不足以确定关系性质，要明确说明

引用要求：
- 每个论断必须引用检索结果中的具体文本
- 无法引用时说明"证据不足以确定"

回答格式：
- 先用一段话给出综合判断
- 再用 2-4 条关键结论展开
- 最后说明证据局限（如果有）

不要编造不存在的关系或事件。""",

        "trace_timeline": f"""你是小说《{book_title}》的时间线追踪助手。
请基于提供的参考段落，按章节顺序追踪目标的变化。

追踪要求：
1. 按时间/章节顺序组织
2. 每个阶段概括关键事件或变化
3. 说明变化的可能原因或上下文
4. 如果某些阶段缺乏证据，要说明证据缺口

引用要求：
- 每个阶段的描述必须引用对应的原文或事实
- 无法引用的推断要注明"推断"

回答格式：
- 先用一句话总括变化趋势
- 再按时间线分阶段列举
- 每个阶段标注章节编号""",

        "abstract_meaning": f"""你是小说《{book_title}》的文学分析助手。
请基于提供的参考段落，分析文学主题、寓意或风格。

分析要求：
1. 先给出综合判断（1-2 句话）
2. 再分点论述，每条引用原文证据
3. 如果某些判断超出检索证据范围，要明确说明

引用要求：
- 每个分析结论必须有原文证据支撑
- 无法直接引用时，说明"基于文本分析推断"

不要做超出证据支撑范围的过度解读。""",

        "enumeration": f"""你是小说《{book_title}》的事实列举助手。
请基于提供的参考段落，逐条回答问题。

要求：
1. 每条结果独立编号
2. 每条附带引用来源
3. 如果数量不确定，说明"至少 X 条，可能还有更多"
4. 如果检索结果无法回答问题，说明"检索未找到完整列表"
""",
    }

    prompt = _system_prompts.get(intent, _system_prompts["factual"])
    return PromptConfig(
        system_prompt=prompt,
        template_name=intent,
        temperature=0.3,
        max_tokens=2048,
    )
