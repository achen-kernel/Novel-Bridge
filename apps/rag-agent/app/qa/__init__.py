"""问答引擎 (QA Engine)

流程:
1. retrieval_runner.hybrid_search: 混合检索 (词法 LIKE + Qdrant 稠密 + ChapterFact)
2. retrieval_runner.knowledge_search: 结构化知识检索 (实体/关系/事件)
3. qa_runner.answer: 组装 context -> 调 DeepSeek/本地 9B -> 生成回答 -> 存储

支持:
- 多轮对话 (历史拼接)
- 实体别名展开检索
- 按章节多样性采样
"""
