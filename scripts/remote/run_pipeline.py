#!/usr/bin/env python3
"""
NovelBridge Pipeline Runner (骨架)

占位脚本，用于未来在远端触发 pipeline 任务。
当前仅解析参数并打印占位信息。

用法:
    python run_pipeline.py --book-id 1 --pipeline import
    python run_pipeline.py --book-id 1 --pipeline extract
    python run_pipeline.py --list-pipelines
"""

import argparse
import sys


AVAILABLE_PIPELINES = {
    "import": "导入书籍并分章分块",
    "extract": "提取 ChapterFact",
    "validate": "验证事实并生成审核数据",
    "index": "构建 Qdrant 向量索引",
    "graph": "投影 Neo4j 叙事图谱",
}


def list_pipelines() -> None:
    print("可用 Pipeline:")
    for name, desc in AVAILABLE_PIPELINES.items():
        print(f"  {name:12s}  {desc}")


def run_pipeline(book_id: int, pipeline: str) -> None:
    if pipeline not in AVAILABLE_PIPELINES:
        print(f"[ERROR] 未知 pipeline: {pipeline}")
        sys.exit(1)

    print(f"[INFO] Pipeline 占位 — 尚未实现")
    print(f"  pipeline : {pipeline} ({AVAILABLE_PIPELINES[pipeline]})")
    print(f"  book_id  : {book_id}")
    print()
    print("[TODO] 调用 rag-agent API 或直接执行 Python pipeline 逻辑")
    print("[TODO] 创建 AgentRun 记录")
    print("[TODO] 执行各 AgentStep")
    print("[TODO] 回写结果到 MySQL")


def main() -> None:
    parser = argparse.ArgumentParser(description="NovelBridge Pipeline Runner")
    parser.add_argument("--book-id", type=int, required=False, help="目标书籍 ID")
    parser.add_argument("--pipeline", type=str, required=False, help="要运行的 pipeline 名称")
    parser.add_argument("--list-pipelines", action="store_true", help="列出可用 pipeline")
    args = parser.parse_args()

    if args.list_pipelines:
        list_pipelines()
        return

    if not args.book_id or not args.pipeline:
        parser.print_help()
        sys.exit(1)

    run_pipeline(args.book_id, args.pipeline)


if __name__ == "__main__":
    main()
