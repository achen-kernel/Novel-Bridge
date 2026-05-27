"""
QA 请求/响应 Schema。
"""
from typing import List, Optional

from pydantic import BaseModel


class QaRequest(BaseModel):
    session_id: int = 0
    book_id: int
    question: str
    use_deepseek: bool = True  # default to DeepSeek API; False for local 9B


class CitationItem(BaseModel):
    """引用条目"""
    source_type: str = "chunk"
    source_id: int = 0
    chapter_id: int = 0
    excerpt: str = ""
    evidence_level: str = "NEAR"
    relevance_score: float = 0.5


class QaResponse(BaseModel):
    """QA 响应"""
    answer: str = ""
    citations: List[CitationItem] = []
