"""
一键全量 Pipeline: P3(Extract) → P4(Govern) → P5(Narrative) → P6(Index) → P7(Graph) → P8(Export)

Usage:
  # 跑一本书
  python run_all.py --book-id 6

  # 跑多本书
  python run_all.py --book-ids 6,7,8,9,10

  # 从P3开始，跳过已完成
  python run_all.py --book-id 6 --skip-done

  # 只跑特定阶段
  python run_all.py --book-id 6 --phases 3,4,5
"""
import argparse
import datetime
import json
import logging
import os
import sys
import time

import httpx

BASE = "http://127.0.0.1:18081"
LOG_DIR = "pipeline_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Phase definitions
PHASES = [
    (3, "Extract (llama-server)", f"/api/books/{{}}/extract", {"use_model": True}, 43200),
    (4, "Entity Governance", f"/api/books/{{}}/govern", {}, 600),
    (5, "Narrative Build", f"/api/books/{{}}/narrative", {}, 600),
    (6, "Index Qdrant", f"/api/books/{{}}/index", {"reindex": False}, 1800),
    (7, "Graph Project (Neo4j)", f"/api/books/{{}}/graph/project", {}, 600),
    (8, "Export ChapterFacts", f"/api/eval/export/chapter-facts?book_id={{}}&min_review=PENDING", {}, 300),
]


def setup_logging(book_ids):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ids_str = "_".join(str(b) for b in book_ids)
    log_file = os.path.join(LOG_DIR, f"pipeline_b{ids_str}_{timestamp}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s][%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(), log_file


def get_book_status(client, book_id):
    """Check book status from API"""
    try:
        r = client.get(f"{BASE}/api/books/{book_id}", timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def call_api(path, body=None, timeout=600, label="", retries=1):
    """POST to rag-agent API with retry"""
    url = f"{BASE}{path}"
    last_error = None
    for attempt in range(1 + retries):
        try:
            t0 = time.time()
            with httpx.Client(timeout=timeout) as c:
                if body:
                    r = c.post(url, json=body)
                else:
                    r = c.post(url)
            elapsed = time.time() - t0
            data = r.json() if r.text else {}
            log.info(f"  [{label}] ✓ {elapsed:.0f}s | {data.get('status','?')} | {data.get('message','')[:100]}")
            return data
        except Exception as e:
            last_error = e
            log.warning(f"  [{label}] ✗ attempt {attempt+1} failed: {e}")
            if attempt < retries:
                time.sleep(3)
    log.error(f"  [{label}] ✗ FAILED after {retries+1} attempts: {last_error}")
    return {"status": "error", "message": str(last_error)}


def run_pipeline(book_ids, phases_to_run, skip_done=False):
    """Run selected phases for each book"""
    client = httpx.Client(timeout=10)
    summary = {str(bid): {} for bid in book_ids}

    for book_id in book_ids:
        log.info(f"{'='*60}")
        log.info(f"Book {book_id}")
        log.info(f"{'='*60}")

        book = get_book_status(client, book_id)
        if not book:
            log.error(f"  Book {book_id} not found via API")
            summary[str(book_id)] = {"error": "Book not found"}
            continue

        log.info(f"  Title: {book.get('title','?')} | Chapters: {book.get('chapter_count',0)}")

        for phase_num, phase_name, url_tmpl, body, timeout in PHASES:
            if phase_num not in phases_to_run:
                continue

            # P6 index: skip if no embedding client available (run on remote only)
            if phase_num == 6:
                log.info(f"  --- P6: {phase_name} ---")
                log.info(f"  ⚠ P6 (Index Qdrant) requires embedding model. "
                         f"Run this on the remote server with: python run_all.py --book-id {book_id} --phases 6")
                summary[str(book_id)]["P6"] = "skipped (embedding on remote)"
                continue

            log.info(f"  --- P{phase_num}: {phase_name} ---")

            # Check skip-done for P3
            if skip_done and phase_num == 3 and book.get('status') == 'EXTRACTED':
                log.info(f"  Already EXTRACTED, skipping P3")
                summary[str(book_id)]["P3"] = "skipped (already done)"
                continue

            path = url_tmpl.format(book_id)
            result = call_api(path, body=body, timeout=timeout, label=f"P{phase_num}")

            status = result.get('status', 'error')
            summary[str(book_id)][f"P{phase_num}"] = status

            if status == 'error':
                log.warning(f"  P{phase_num} failed, continuing to next phase")

        log.info("")

    client.close()
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run NovelBridge pipeline P3-P8")
    parser.add_argument("--book-id", type=int, help="Single book ID")
    parser.add_argument("--book-ids", type=str, help="Comma-separated book IDs")
    parser.add_argument("--phases", type=str, default="3,4,5,6,7,8", help="Comma-separated phase numbers")
    parser.add_argument("--skip-done", action="store_true", help="Skip already processed books")
    args = parser.parse_args()

    if args.book_id:
        book_ids = [args.book_id]
    elif args.book_ids:
        book_ids = [int(b.strip()) for b in args.book_ids.split(",")]
    else:
        print("Error: specify --book-id or --book-ids")
        sys.exit(1)

    phases_to_run = [int(p.strip()) for p in args.phases.split(",")]

    log, log_file = setup_logging(book_ids)
    log.info(f"Books: {book_ids}")
    log.info(f"Phases: {phases_to_run}")
    log.info(f"Skip done: {args.skip_done}")
    log.info(f"Log: {log_file}")
    log.info("")

    t_start = time.time()
    summary = run_pipeline(book_ids, phases_to_run, args.skip_done)

    elapsed = time.time() - t_start
    log.info(f"{'='*60}")
    log.info(f"Pipeline complete in {elapsed:.0f}s")
    log.info(f"Summary: {json.dumps(summary, ensure_ascii=False, indent=2)}")
    log.info(f"Log saved to: {log_file}")


if __name__ == "__main__":
    main()
