"""
Smart text splitter for oversized chunks.

Splits text exceeding max_chars at roughly the midpoint,
preferring natural boundaries (paragraph → sentence → line → word).
Recursively splits if pieces still exceed max_chars.
Tracks relationships between split segments.

If hard rules can't find a good split point, falls back to LLM.
"""
import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# Default max chars for Qwen3-Embedding-0.6B (supports 48K tokens, ~50K chars)
DEFAULT_MAX_CHARS = 50000

# Window for searching natural boundaries around the midpoint (±chars)
SEARCH_WINDOW = 1000


@dataclass
class SplitSegment:
    """A segment resulting from splitting oversized text."""
    text: str
    split_index: int          # 0-based order in the split sequence
    total_splits: int         # Total number of pieces this text was split into
    parent_chunk_id: Optional[int] = None  # Original chunk ID (set by caller)
    split_strategy: str = "exact_half"     # How this split was decided
    # For Qdrant payload: points from same parent share parent_chunk_id
    # and are ordered by split_index


def find_split_near(
    position: int,
    text: str,
    delimiter: str,
    window: int = SEARCH_WINDOW,
    include_delimiter: bool = True,
) -> Optional[int]:
    """Find the delimiter nearest to *position* within *window* chars.

    Returns the index *after* the delimiter (suitable for splitting),
    or None if not found.
    """
    start = max(0, position - window)
    end = min(len(text), position + window)

    # Search forward from position
    forward = text.find(delimiter, position, end)
    # Search backward from position
    backward = text.rfind(delimiter, start, position)

    if forward == -1 and backward == -1:
        return None

    offset = len(delimiter) if include_delimiter else 0
    if forward == -1:
        return backward + offset
    if backward == -1:
        return forward + offset

    # Pick the one closer to the target position
    if abs(forward - position) <= abs(backward - position):
        return forward + offset
    else:
        return backward + offset


# Priority-ordered delimiters for natural boundary search
# (paragraph >> sentence >> line >> phrase >> word)
SPLIT_DELIMITERS = [
    ("\n\n",      True,   "paragraph"),   # Paragraph break
    ("\n",        True,   "line"),         # Line break
    ("。",         True,   "sentence_zh"),  # Chinese period
    ("！",         True,   "exclamation"),  # Chinese exclamation
    ("？",         True,   "question_zh"),  # Chinese question mark
    (".\n",       True,   "sentence_en"),  # English sentence + newline
    ("。\"",      True,   "quote_zh"),     # Chinese closing quote
    ("。』",      True,   "quote_tw"),     # Taiwanese closing quote
    ("\u3000",    False,  "ideographic_space"),  # Full-width space
    ("，",         False,  "comma_zh"),     # Chinese comma
    (", ",        False,  "comma_en"),     # English comma + space
    (" ",         False,  "word"),         # Word boundary (last resort before exact half)
]


_llm_split_callback: Optional[Callable[[str, int], Optional[int]]] = None


def register_llm_splitter(callback: Callable[[str, int], Optional[int]]):
    """Register an LLM-based split function.

    The callback receives (full_text, approx_position) and returns
    the split index, or None if it can't decide.
    """
    global _llm_split_callback
    _llm_split_callback = callback


def _llm_split(text: str, approx_position: int) -> Optional[int]:
    """Try to call the registered LLM splitter."""
    if _llm_split_callback is None:
        return None
    try:
        return _llm_split_callback(text, approx_position)
    except Exception as e:
        logger.warning(f"LLM splitter failed: {e}")
        return None


def smart_split_text(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    parent_chunk_id: Optional[int] = None,
) -> List[SplitSegment]:
    """Recursively split text at ~halfway when it exceeds *max_chars*.

    Strategy priority:
      1. Natural paragraph/sentence boundaries near midpoint
      2. LLM fallback (if registered)
      3. Exact character midpoint

    Returns a list of SplitSegments with relationship tracking.
    """
    if len(text) <= max_chars:
        return [SplitSegment(
            text=text,
            split_index=0,
            total_splits=1,
            parent_chunk_id=parent_chunk_id,
            split_strategy="none",
        )]

    mid = len(text) // 2

    # --- Strategy 1: Natural boundaries ---
    split_pos = None
    strategy = "exact_half"
    for delim, include_delim, strat_name in SPLIT_DELIMITERS:
        pos = find_split_near(mid, text, delim, include_delimiter=include_delim)
        if pos is not None and 0 < pos < len(text):
            split_pos = pos
            strategy = strat_name
            logger.debug(f"Split at '{delim}' ({strat_name}) pos={pos} for {len(text)}-char text")
            break

    # --- Strategy 2: LLM fallback ---
    if split_pos is None:
        llm_pos = _llm_split(text, mid)
        if llm_pos is not None and 0 < llm_pos < len(text):
            split_pos = llm_pos
            strategy = "llm"
            logger.debug(f"LLM split at pos={llm_pos} for {len(text)}-char text")

    # --- Strategy 3: Exact half ---
    if split_pos is None:
        split_pos = mid
        strategy = "exact_half"
        logger.debug(f"Exact half split at pos={split_pos} for {len(text)}-char text")

    # Safety: ensure split_pos is valid
    if split_pos <= 0 or split_pos >= len(text):
        split_pos = mid
        strategy = "exact_half"

    left = text[:split_pos]
    right = text[split_pos:]

    # Recursively split both halves
    left_segments = smart_split_text(left, max_chars, parent_chunk_id)
    right_segments = smart_split_text(right, max_chars, parent_chunk_id)

    # Merge and re-index
    all_segments = left_segments + right_segments
    total = len(all_segments)
    for i, seg in enumerate(all_segments):
        seg.split_index = i
        seg.total_splits = total
        if seg.split_strategy == "none":
            seg.split_strategy = strategy  # Propagate the strategy that caused the split

    return all_segments


def truncate_head(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Simple head truncation (fallback for single-text use)."""
    if len(text) > max_chars:
        logger.warning(f"Truncating text from {len(text)} to {max_chars} chars (head)")
        return text[:max_chars]
    return text
