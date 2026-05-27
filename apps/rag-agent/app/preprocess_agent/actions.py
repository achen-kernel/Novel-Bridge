"""PreprocessAgent action names.

Each action should wrap existing app.pipeline functionality instead of moving
pipeline logic into the Agent.
"""

from enum import Enum


class PreprocessAction(str, Enum):
    REGISTER_SOURCE = "register_source"
    DECODE_SOURCE = "decode_source"
    SPLIT_CHAPTERS = "split_chapters"
    BUILD_CHUNKS = "build_chunks"
    BUILD_PRIOR = "build_prior"
    EXTRACT_MENTIONS = "extract_mentions"
    BUILD_CHAPTER_FACTS = "build_chapter_facts"
    GOVERN_ENTITIES = "govern_entities"
    AGGREGATE_FACTS = "aggregate_facts"
    RUN_QUALITY = "run_quality"
    INDEX_RETRIEVAL = "index_retrieval"
    PROJECT_GRAPH = "project_graph"
    EXPORT_DATASET = "export_dataset"
