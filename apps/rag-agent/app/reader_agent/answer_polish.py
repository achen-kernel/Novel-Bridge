"""@NB-ENTRYPOINT Stage 6E/6G/P3 answer polish, audit, and model-based audit.

Pure functions — no model calls, no DB reads/writes (except audit_deepseek).
Used to clean up model output before presenting to the user.

P3 addition:
- audit_deepseek(): calls DeepSeek to verify claims against evidence.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════
# Audit result
# ═════════════════════════════════════════════════════════════════════


@dataclass
class AuditResult:
    """Result of answer audit — captures quality signals."""

    unsupported_claims: list[str] = field(default_factory=list)
    citation_count: int = 0
    total_claims: int = 0
    has_broad_claims: bool = False
    has_punctuation_issues: bool = False
    has_repetition: bool = False
    length: int = 0
    warnings: list[str] = field(default_factory=list)


# ═════════════════════════════════════════════════════════════════════
# Citation tag cleanup
# ═════════════════════════════════════════════════════════════════════


def strip_citation_tags(text: str) -> str:
    """Remove HTML-style <cite> tags and internal ids."""
    result = text
    result = re.sub(r"<cite\b[^>]*>.*?</cite>", "", result, flags=re.IGNORECASE | re.DOTALL)
    result = re.sub(r"<cite\b[^>]*/?>", "", result, flags=re.IGNORECASE)
    return result


# ═════════════════════════════════════════════════════════════════════
# Chunk / run ID cleanup
# ═════════════════════════════════════════════════════════════════════


def strip_internal_ids(text: str) -> str:
    """Remove patterns like [chunk_123], run_456, id=789."""
    result = text
    result = re.sub(r"\[chunk_\d+\]", "", result)
    result = re.sub(r"\brun_\d+\b", "", result)
    result = re.sub(r"\bid[:：]\s*\d+", "", result)
    result = re.sub(r"\bchunk\s*#?\s*\d+\b", "", result)
    return result


# ═════════════════════════════════════════════════════════════════════
# Punctuation cleanup
# ═════════════════════════════════════════════════════════════════════


def clean_duplicate_punctuation(text: str) -> str:
    """Compress repeated punctuation like 。。 → 。、；。→ ；、，。→ 。"""
    result = text
    result = re.sub(r"。{2,}", "。", result)
    result = re.sub(r"？{2,}", "？", result)
    result = re.sub(r"！{2,}", "！", result)
    result = re.sub(r"[；;][。.]", "。", result)
    result = re.sub(r"[，,][。.]", "。", result)
    result = re.sub(r"[。.]，", "。", result)
    return result


def strip_trailing_punctuation(text: str) -> str:
    """Remove trailing punctuation from the entire text."""
    return text.rstrip("。，；：、？！.,;:!? \t\n\r")


# ═════════════════════════════════════════════════════════════════════
# Whitespace cleanup
# ═════════════════════════════════════════════════════════════════════


def collapse_whitespace(text: str) -> str:
    """Compress excessive whitespace."""
    result = text
    result = re.sub(r" {2,}", " ", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = re.sub(r" \n", "\n", result)
    result = re.sub(r"\n ", "\n", result)
    return result.strip()


# ═════════════════════════════════════════════════════════════════════
# Unsupported-claim detection
# ═════════════════════════════════════════════════════════════════════

# Broad/unsupported claim patterns — claims that need stronger evidence
_BROAD_CLAIM_PATTERNS = [
    r"古代百科全书",
    r"无所不包",
    r"涵盖一切",
    r"最为全面",
    r"最重要的",
    r"唯一[\S]{0,4}的",
    r"毫无疑问",
    r"毋庸置疑",
    r"众所周知",
    r"人人皆知",
    r"公认的",
    r"最高的成就",
    r"巅峰之作",
    r"绝无仅有",
    r"空前绝后",
    r"所有[\S]{0,4}都",
    r"没有任何[\S]{0,4}不",
    r"奠定了[\S]{0,4}基础",
]

# Markers that suggest a claim might not be directly supported
_UNSUPPORTED_MARKERS = [
    "可能", "或许", "大概", "似乎", "一般认为",
    "有观点认为", "据推测", "据传", "传说",
    "有学者认为", "学术界认为",
]


def detect_unsupported_claims(text: str) -> list[str]:
    """Detect potentially unsupported broad claims in model output.

    Returns a list of problematic claim excerpts.
    This is heuristic — not a guarantee of actual support.
    """
    issues: list[str] = []
    if not text:
        return issues

    for pattern in _BROAD_CLAIM_PATTERNS:
        matches = re.finditer(pattern, text)
        for m in matches:
            start = max(0, m.start() - 20)
            end = min(len(text), m.end() + 20)
            excerpt = text[start:end].strip()
            if excerpt:
                issues.append(excerpt)

    return issues


def count_broad_claims(text: str) -> int:
    """Count how many broad/unsupported claim patterns appear."""
    count = 0
    for pattern in _BROAD_CLAIM_PATTERNS:
        count += len(re.findall(pattern, text))
    return count


# ═════════════════════════════════════════════════════════════════════
# Repetition detection
# ═════════════════════════════════════════════════════════════════════


def has_repetition(text: str) -> bool:
    """Check if text has repeated sentences or ideas."""
    if not text:
        return False
    sentences = re.split(r"[。！？!?]", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 8]
    unique = set()
    repeat_count = 0
    for s in sentences:
        # Check if this sentence is similar to any seen
        if s in unique:
            repeat_count += 1
        else:
            unique.add(s)
    return repeat_count >= 1


# ═════════════════════════════════════════════════════════════════════
# Provider-aware polish
# ═════════════════════════════════════════════════════════════════════


def polish_local_9b(text: str) -> str:
    """Polish for local 9B output — full cleanup.

    9B tends to:
    - Have more punctuation artifacts
    - Preserve internal citation tags
    - Repeat ideas
    - Drift into broad claims
    """
    result = text
    result = strip_citation_tags(result)
    result = strip_internal_ids(result)
    result = clean_duplicate_punctuation(result)
    result = collapse_whitespace(result)
    result = strip_trailing_punctuation(result)
    return result


def polish_deepseek(text: str) -> str:
    """Polish for DeepSeek output — lighter cleanup.

    DeepSeek produces cleaner output, so we only:
    - Strip citation tags (still present from RAG context)
    - Light punctuation cleanup
    - Whitespace normalization
    """
    result = text
    result = strip_citation_tags(result)
    result = clean_duplicate_punctuation(result)
    result = collapse_whitespace(result)
    return result.strip()


def polish(text: str, provider: str = "local") -> str:
    """Apply provider-aware polish.

    Args:
        text: Raw model output text.
        provider: "local" or "deepseek" (default "local").

    Returns:
        Cleaned text appropriate for the provider.
    """
    if not text:
        return text
    if provider == "deepseek":
        return polish_deepseek(text)
    return polish_local_9b(text)


# ═════════════════════════════════════════════════════════════════════
# Model-based audit (P3)
# ═════════════════════════════════════════════════════════════════════


async def audit_deepseek(
    answer: str,
    evidence_text: str | None = None,
) -> AuditResult:
    """Use DeepSeek to audit an answer against evidence.

    Checks each key claim for evidence support.
    Falls back to pattern-based audit if DeepSeek unavailable.
    """
    if not answer:
        return AuditResult()

    try:
        from app.clients.deepseek_client import deepseek_client

        prompt = f"""你是一个答案质量审计员。检查以下回答中的每条关键论断是否被提供的证据支撑。

回答：
{answer[:2000]}

证据：
{evidence_text or '(未提供证据文本)'}

请逐条检查：
1. 每条论断是否有证据支撑？
2. 是否存在没有证据支持的 broad claim？
3. 是否存在重复或矛盾的内容？

输出 JSON（纯 JSON，不要 markdown 标记）：
{{
  "unsupported_claims": ["没有证据支撑的论断1", "论断2"],
  "total_claims_checked": 5,
  "has_broad_claims": true/false,
  "has_repetition": true/false,
  "warnings": ["审计发现的问题"]
}}

如果没有发现问题，unsupported_claims 返回空数组，warnings 返回空数组。
"""
        text = await deepseek_client.chat(
            messages=[
                {"role": "system", "content": "你是严谨的答案审计员，只基于证据做判断。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=600,
        )
        if not text:
            return audit(answer)  # fallback

        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        import json as _json
        data = _json.loads(text)
        unsupported = data.get("unsupported_claims", [])
        warnings = data.get("warnings", [])

        return AuditResult(
            unsupported_claims=unsupported if isinstance(unsupported, list) else [],
            total_claims=data.get("total_claims_checked", 0),
            has_broad_claims=bool(data.get("has_broad_claims")),
            has_repetition=bool(data.get("has_repetition")),
            length=len(answer),
            warnings=warnings if isinstance(warnings, list) else [],
        )
    except Exception as e:
        logger.warning("DeepSeek audit failed, falling back to pattern audit: %s", e)
        return audit(answer)  # fallback to pattern-based


# ═════════════════════════════════════════════════════════════════════
# Full audit (pattern-based, used as default and as fallback for audit_deepseek)
# ═════════════════════════════════════════════════════════════════════


def audit(text: str) -> AuditResult:
    """Run audit checks on model output.

    Returns AuditResult with detected issues.
    Does NOT modify the text.
    """
    if not text:
        return AuditResult()

    unsupported = detect_unsupported_claims(text)
    broad_count = count_broad_claims(text)
    has_punct = bool(re.search(r"[。，；：？！]{2,}|[；;][。.]", text))
    has_repeat = has_repetition(text)

    warnings: list[str] = []
    if unsupported:
        warnings.append(f"检测到 {len(unsupported)} 处可能缺乏直接支持的论断")
    if has_punct:
        warnings.append("输出存在标点符号问题")
    if has_repeat:
        warnings.append("输出存在内容重复")

    return AuditResult(
        unsupported_claims=unsupported,
        citation_count=len(re.findall(r"<cite", text, re.IGNORECASE)),
        total_claims=broad_count + len(unsupported),
        has_broad_claims=broad_count > 0,
        has_punctuation_issues=has_punct,
        has_repetition=has_repeat,
        length=len(text),
        warnings=warnings,
    )

