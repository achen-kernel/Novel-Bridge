"""
全量重跑脚本 —— 清理旧数据后重跑 5 本书的 P3-P8 Pipeline。

使用方式：
  1. 确保 rag-agent 运行中（http://127.0.0.1:18079）
  2. 确认远端服务（MySQL/Qdrant/Neo4j/llama-server/DeepSeek）健康
  3. python scripts/pipeline/re_run_all_books.py

步骤：
  STEP 1: 清理 MySQL 衍生数据（保留 novel_book 原文）
  STEP 2: 清理 Qdrant 向量
  STEP 3: 清理 Neo4j 图数据
  STEP 4: 重置 book.status = 'IMPORTED'
  STEP 5: 逐书触发 P3 → P4 → P5 → P6(reindex) → P7 → P8

高风险提醒：
  - 清理操作不可逆！如果不确定，先备份 MySQL 和 Neo4j。
  - Neo4j 清理只删除 book_id 标记的节点（修复了旧版全局 clear 问题）
  - 搜神记(8)和山海经(9)因文言文分块策略修改，chunk 数会和旧版不同
"""

import asyncio
import json
import logging
import sys
import time

import httpx

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

# ── 配置 ──
API_BASE = "http://127.0.0.1:18079"
QDRANT_BASE = "http://127.0.0.1:16333"

BOOK_IDS = [6, 7, 8, 9, 10]  # 西游记, 聊斋, 搜神记, 山海经, 水浒传
BOOK_NAMES = {6: "西游记", 7: "聊斋志异", 8: "搜神记", 9: "山海经", 10: "水浒传"}

# ── MySQL 清理 SQL ──
CLEANUP_SQL = """
-- 清理教材：按 book_id 删除所有 pipeline 产出数据
-- 保留 novel_book（书籍原文 + prior_hint）
DELETE FROM novel_plot_stage WHERE book_id IN ({book_ids});
DELETE FROM novel_event_fact WHERE book_id IN ({book_ids});
DELETE FROM novel_event_mention WHERE book_id IN ({book_ids});
DELETE FROM novel_relation_fact WHERE book_id IN ({book_ids});
DELETE FROM novel_relation_mention WHERE book_id IN ({book_ids});
DELETE FROM novel_alias_decision WHERE book_id IN ({book_ids});
DELETE FROM novel_entity_profile WHERE book_id IN ({book_ids});
DELETE FROM novel_entity_mention WHERE book_id IN ({book_ids});
DELETE FROM novel_model_call WHERE book_id IN ({book_ids});
DELETE FROM novel_chapter_fact WHERE book_id IN ({book_ids});
DELETE FROM novel_chunk WHERE book_id IN ({book_ids});
DELETE FROM novel_chapter WHERE book_id IN ({book_ids});

-- 重置 book 状态
UPDATE novel_book SET status='IMPORTED', chapter_count=0, chunk_count=0 WHERE id IN ({book_ids});
"""


async def check_health() -> bool:
    """确认 rag-agent 和依赖服务健康"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # rag-agent health
            r = await client.get(f"{API_BASE}/health")
            if r.status_code != 200:
                logger.error(f"rag-agent health failed: {r.status_code}")
                return False
            logger.info(f"✅ rag-agent: {r.json()}")

            # Qdrant health
            r = await client.get(f"{QDRANT_BASE}/healthz")
            if r.status_code != 200:
                logger.warning(f"Qdrant healthz: {r.status_code} (proceeding anyway)")
            else:
                logger.info("✅ Qdrant: healthy")

            return True
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


async def step1_cleanup_mysql():
    """STEP 1: 清理 MySQL 衍生数据（通过 API 或直接 SQL）"""
    logger.info("=" * 50)
    logger.info("STEP 1: 清理 MySQL 衍生数据")

    # 尝试通过 health/mysql 确认 MySQL 可达
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{API_BASE}/health/mysql")
            if r.status_code != 200:
                logger.error("MySQL not reachable! Cannot proceed.")
                return False
            logger.info(f"MySQL: {r.json()}")
        except Exception as e:
            logger.error(f"MySQL health check failed: {e}")
            return False

    # 由于没有 API endpoint 做批量 cleanup，这里输出 SQL 让用户手动执行
    book_ids_str = ",".join(str(b) for b in BOOK_IDS)
    logger.warning("=" * 60)
    logger.warning("请打开 MySQL 客户端（如 DBeaver/HeidiSQL），在远端数据库执行以下 SQL：")
    logger.warning("=" * 60)
    print()
    print(CLEANUP_SQL.format(book_ids=book_ids_str))
    print()
    logger.warning("=" * 60)
    logger.warning("执行完毕后按 Enter 继续...")
    logger.warning("=" * 60)
    input()
    return True


async def step2_cleanup_qdrant():
    """STEP 2: 清理 Qdrant 向量"""
    logger.info("=" * 50)
    logger.info("STEP 2: 清理 Qdrant 向量")

    async with httpx.AsyncClient(timeout=30) as client:
        for bid in BOOK_IDS:
            for collection in ["novel_chunks", "novel_facts"]:
                # 通过 reindex API 先删后建
                logger.info(f"  清理 {collection} 中 book_id={bid} 的向量...")
                try:
                    r = await client.post(
                        f"{API_BASE}/api/books/{bid}/index",
                        json={"reindex": True},
                        timeout=120,
                    )
                    result = r.json()
                    logger.info(f"  → {collection}: {result.get('status', 'unknown')} "
                                f"(chunks={result.get('chunks_indexed', 0)}, "
                                f"facts={result.get('facts_indexed', 0)})")
                    # 注意：reindex=True 会先删后建 -> 此处只是为了删除数据
                    # 实际索引会在 STEP 5 重新建
                except Exception as e:
                    logger.warning(f"  → Qdrant cleanup failed for book {bid}: {e}")

    logger.info("✅ Qdrant 清理完成（临时索引不会保留，STEP 5 重新索引）")
    return True


async def step3_cleanup_neo4j():
    """STEP 3: 清理 Neo4j 图数据（按 book_id 范围）"""
    logger.info("=" * 50)
    logger.info("STEP 3: 清理 Neo4j 图数据")

    async with httpx.AsyncClient(timeout=30) as client:
        for bid in BOOK_IDS:
            logger.info(f"  清理 book_id={bid} 的 Neo4j 数据...")
            # P7 现在使用 clear_book(book_id) 而非全局 clear_all
            # 但为了彻底清除，重新投影时用 clear_first=True
            try:
                r = await client.post(
                    f"{API_BASE}/api/books/{bid}/graph/project",
                    timeout=30,
                )
                result = r.json()
                logger.info(f"  → Neo4j: {result.get('status', 'unknown')}")
            except Exception as e:
                logger.warning(f"  → Neo4j cleanup failed for book {bid}: {e}")

    logger.info("✅ Neo4j 清理完成（临时投影不会保留，STEP 5 重新投影）")
    return True


async def step4_reset_book_status():
    """STEP 4: 重置 book 状态（已通过 SQL 完成，这里仅检查）"""
    logger.info("=" * 50)
    logger.info("STEP 4: 确认 book 状态已重置")

    async with httpx.AsyncClient(timeout=10) as client:
        for bid in BOOK_IDS:
            r = await client.get(f"{API_BASE}/api/books/{bid}")
            if r.status_code == 200:
                book = r.json()
                logger.info(f"  {BOOK_NAMES[bid]}({bid}): status={book.get('status', '?')}")
            else:
                logger.warning(f"  {BOOK_NAMES[bid]}({bid}): API error {r.status_code}")

    logger.info("✅ Book 状态确认完成")


async def step5_run_pipeline():
    """STEP 5: 逐书触发 P3 → P4 → P5 → P6 → P7 → P8"""
    logger.info("=" * 50)
    logger.info("STEP 5: 全量重跑 Pipeline P3-P8")

    total_start = time.time()

    for bid in BOOK_IDS:
        book_name = BOOK_NAMES[bid]
        logger.info(f"\n{'=' * 40}")
        logger.info(f"开始处理: {book_name}({bid})")
        logger.info(f"{'=' * 40}")

        phases = [
            ("P3", f"{API_BASE}/api/books/{bid}/extract", {"use_model": True}),
            ("P4", f"{API_BASE}/api/books/{bid}/govern", {}),
            ("P5", f"{API_BASE}/api/books/{bid}/narrative", {}),
            ("P6", f"{API_BASE}/api/books/{bid}/index", {"reindex": True}),
            ("P7", f"{API_BASE}/api/books/{bid}/graph/project", {}),
            ("P8", f"{API_BASE}/api/eval/export/chapter-facts?book_id={bid}&min_review=PENDING", None),
        ]

        async with httpx.AsyncClient(timeout=43200) as client:  # 12h timeout for P3
            for phase_name, url, body in phases:
                phase_start = time.time()
                logger.info(f"  [{phase_name}] 开始...")

                try:
                    if body is not None:
                        r = await client.post(url, json=body)
                    else:
                        r = await client.get(url)

                    elapsed = time.time() - phase_start
                    if r.status_code == 200:
                        result = r.json()
                        status = result.get('status', result)
                        logger.info(f"  [{phase_name}] ✅ {elapsed:.0f}s - {status}")
                    else:
                        logger.error(f"  [{phase_name}] ❌ {elapsed:.0f}s - HTTP {r.status_code}: {r.text[:200]}")

                except Exception as e:
                    elapsed = time.time() - phase_start
                    logger.error(f"  [{phase_name}] ❌ {elapsed:.0f}s - Exception: {e}")

    total_elapsed = time.time() - total_start
    logger.info(f"\n{'=' * 50}")
    logger.info(f"全量重跑完成！总耗时: {total_elapsed:.0f}s ({total_elapsed/60:.1f}min)")
    logger.info(f"{'=' * 50}")


async def main():
    logger.info("=" * 60)
    logger.info("NovelBridge 全量重跑脚本")
    logger.info(f"书籍: {', '.join(f'{BOOK_NAMES[b]}({b})' for b in BOOK_IDS)}")
    logger.info(f"API: {API_BASE}")
    logger.info(f"Qdrant: {QDRANT_BASE}")
    logger.info("=" * 60)
    print()

    # 0. Health check
    logger.info("检查服务健康状态...")
    if not await check_health():
        logger.error("Health check 失败，终止。")
        sys.exit(1)
    print()

    # 1. MySQL cleanup
    if not await step1_cleanup_mysql():
        logger.error("MySQL 清理失败，终止。")
        sys.exit(1)
    print()

    # 2. Qdrant cleanup
    await step2_cleanup_qdrant()
    print()

    # 3. Neo4j cleanup
    await step3_cleanup_neo4j()
    print()

    # 4. Verify reset
    await step4_reset_book_status()
    print()

    # 5. Run pipeline
    logger.info("准备开始全量重跑。确认按 Enter...")
    input()
    await step5_run_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
