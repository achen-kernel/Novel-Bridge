"""质量提升工作流 (Quality Improvement)

stages/
  entity_name_normalizer:  relation_fact 实体名 -> entity_profile canonical_name 对齐
  relation_deduper:         双向重复关系合并 (标记 MERGED)
  event_summarizer:         空 summary 填充 (骨架, 暂无空数据)

编排器 quality_workflow.py 支持 run_all / run_stage
"""
