"""预处理管线 (Preprocessing Pipeline)

完整的 P1-P8 小说处理流程:

P1 (book_processor + splitter + chunker): 原始文本 -> 章节 -> Chunk
P2 (prior_hint): DeepSeek API 生成书籍梗概 (已并入 P0)
P3 (extraction_runner + fact_pipeline_runner): Chunk -> 实体/关系/事件抽取 -> ChapterFact
P4 (entity_governance_runner): 别名决策 -> 实体画像
P5 (narrative_builder): 跨章事件聚合 -> EventFact
P6 (index_runner): ChapterFact -> Qdrant 向量索引
P7 (graph_projector): 实体/关系/事件 -> Neo4j 知识图谱
P8 (dataset_exporter): ChapterFact -> 训练数据 (JSONL)

每个阶段可独立运行, 见 scripts/pipeline/run_all.py
"""
