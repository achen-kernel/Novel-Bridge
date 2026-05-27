"""评估系统 (Evaluation)

- eval_runner: 遍历 eval case -> 调 QA -> 多维评分 -> 报告
- eval_store: 评估用例/运行/结果持久化
- 评分维度: has_answer + citation_count + answer_quality
"""
