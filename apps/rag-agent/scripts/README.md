# rag-agent 脚本目录

| 子目录 | 用途 | 示例 |
|--------|------|------|
| `pipeline/` | Pipeline 编排脚本（全量跑 P3-P8） | `run_all.py --book-id 6` |
| `check/` | 数据检查/审计 | `check_config.py`, `check_db.py` |
| `test/` | QA 功能测试 | `test_qa_baseline.py`, `test_failing_cases.py` |
| `debug/` | 诊断/调查 | `debug_alias_lookup.py`, `investigate_quality.sh` |
| `ops/` | 运维操作（修复/清洗/重索引） | `fix_b10.py`, `clean_b7.py`, `reindex_all.py` |

运行方式（从 rag-agent 根目录）：
```powershell
python scripts/pipeline/run_all.py --book-id 6
python scripts/test/test_qa_baseline.py
```
