"""
Extraction strategy abstraction — pluggable backends for P3 extraction.

Currently implemented: Local9B (llama-server via SSH tunnel).
Future: DeepSeek API (batch multiple chapters per call).
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.clients.model_client import ModelClient

logger = logging.getLogger(__name__)


class ExtractionStrategy(ABC):
    """Abstract extraction strategy for Stage 2 (P3)."""

    @abstractmethod
    async def extract_chapter(self, book_id: int, chapter_number: int, chapter_title: str,
                               book_title: str, chunks: list[dict]) -> dict:
        """Process one chapter's chunks and return merged extraction result.

        Args:
            book_id: Book ID
            chapter_number: Logical chapter number
            chapter_title: Chapter title
            book_title: Book title
            chunks: List of chunk dicts, each with 'id', 'content'

        Returns:
            dict with extracted entities, relations, events, chapter_summary
        """
        ...

    @abstractmethod
    async def get_max_concurrency(self) -> int:
        """How many chapters can be processed concurrently.

        Local 9B: 1 (single-threaded inference)
        DeepSeek API: 5 (API rate limit dependent)
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy display name."""
        ...


class Local9BExtraction(ExtractionStrategy):
    """Extract using local llama-server 9B model (one chunk at a time)."""

    def __init__(self, prior_hint: Optional[dict] = None):
        self.prior_hint = prior_hint or {}
        self._client = ModelClient(provider="local")

    @property
    def name(self) -> str:
        return "Local 9B"

    async def get_max_concurrency(self) -> int:
        return 1

    async def extract_chapter(self, book_id: int, chapter_number: int, chapter_title: str,
                               book_title: str, chunks: list[dict]) -> dict:
        """Process chunks sequentially using local 9B."""
        from app.pipeline.extraction_runner import extract_chunk

        chunk_results = []
        for ck in chunks:
            result = await extract_chunk(
                chunk_text=ck['content'],
                chapter_title=chapter_title,
                book_title=book_title,
                chapter_id=chapter_number,
                chunk_id=ck['id'],
                use_model=True,
                prior_hint=self.prior_hint,
                provider="local",
            )
            chunk_results.append(result)

        # Merge chunk results
        chapter_summary = ""
        for cr in chunk_results:
            summary = cr.get('chapter_summary', '') or ''
            if summary:
                chapter_summary = summary
                break

        return {
            "chunk_results": chunk_results,
            "chapter_summary": chapter_summary,
        }


class DeepSeekExtraction(ExtractionStrategy):
    """Extract using DeepSeek API (batch multiple chunks per call).

    NOT YET IMPLEMENTED — placeholder for future development.
    """

    def __init__(self, prior_hint: Optional[dict] = None):
        self.prior_hint = prior_hint or {}

    @property
    def name(self) -> str:
        return "DeepSeek API"

    async def get_max_concurrency(self) -> int:
        return 5  # API can handle multiple concurrent requests

    async def extract_chapter(self, book_id: int, chapter_number: int, chapter_title: str,
                               book_title: str, chunks: list[dict]) -> dict:
        """Not implemented yet."""
        raise NotImplementedError("DeepSeek API extraction not implemented yet")


def get_strategy(provider: str, prior_hint: Optional[dict] = None) -> ExtractionStrategy:
    """Factory: return the appropriate strategy for the given provider."""
    if provider == "deepseek":
        return DeepSeekExtraction(prior_hint)
    return Local9BExtraction(prior_hint)
