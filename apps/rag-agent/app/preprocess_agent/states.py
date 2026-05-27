"""PreprocessAgent state contract."""

from enum import Enum


class PreprocessState(str, Enum):
    NEW = "NEW"
    SOURCE_REGISTERED = "SOURCE_REGISTERED"
    SOURCE_DECODED = "SOURCE_DECODED"
    CHAPTERS_SPLIT = "CHAPTERS_SPLIT"
    CHUNKS_BUILT = "CHUNKS_BUILT"
    PRIOR_READY = "PRIOR_READY"
    MENTIONS_EXTRACTED = "MENTIONS_EXTRACTED"
    CHAPTER_FACTS_BUILT = "CHAPTER_FACTS_BUILT"
    ENTITIES_GOVERNED = "ENTITIES_GOVERNED"
    FACTS_AGGREGATED = "FACTS_AGGREGATED"
    QUALITY_CHECKED = "QUALITY_CHECKED"
    INDEXED = "INDEXED"
    GRAPH_PROJECTED = "GRAPH_PROJECTED"
    DATASET_EXPORTED = "DATASET_EXPORTED"
    DONE = "DONE"
    NEED_REVIEW = "NEED_REVIEW"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


PREPROCESS_TRANSITIONS = [
    (PreprocessState.NEW, PreprocessState.SOURCE_REGISTERED),
    (PreprocessState.SOURCE_REGISTERED, PreprocessState.SOURCE_DECODED),
    (PreprocessState.SOURCE_DECODED, PreprocessState.CHAPTERS_SPLIT),
    (PreprocessState.CHAPTERS_SPLIT, PreprocessState.CHUNKS_BUILT),
    (PreprocessState.CHUNKS_BUILT, PreprocessState.PRIOR_READY),
    (PreprocessState.PRIOR_READY, PreprocessState.MENTIONS_EXTRACTED),
    (PreprocessState.MENTIONS_EXTRACTED, PreprocessState.CHAPTER_FACTS_BUILT),
    (PreprocessState.CHAPTER_FACTS_BUILT, PreprocessState.ENTITIES_GOVERNED),
    (PreprocessState.ENTITIES_GOVERNED, PreprocessState.FACTS_AGGREGATED),
    (PreprocessState.FACTS_AGGREGATED, PreprocessState.QUALITY_CHECKED),
    (PreprocessState.QUALITY_CHECKED, PreprocessState.INDEXED),
    (PreprocessState.INDEXED, PreprocessState.GRAPH_PROJECTED),
    (PreprocessState.GRAPH_PROJECTED, PreprocessState.DATASET_EXPORTED),
    (PreprocessState.DATASET_EXPORTED, PreprocessState.DONE),
]

for _state in list(PreprocessState):
    if _state not in {
        PreprocessState.DONE,
        PreprocessState.FAILED,
        PreprocessState.CANCELED,
        PreprocessState.NEED_REVIEW,
    }:
        PREPROCESS_TRANSITIONS.extend(
            [
                (_state, PreprocessState.NEED_REVIEW),
                (_state, PreprocessState.FAILED),
                (_state, PreprocessState.CANCELED),
            ]
        )
