"""
Pipeline for Books 6, 7, 9, 10 - local rag-agent (port 18081), remote llama-server via SSH tunnel
Phase 6 (index Qdrant) is SKIPPED - embedding model runs on remote server only.
Phase 7 (graph project) into Neo4j.

Usage: conda activate svm && cd apps/rag-agent && python run_6710.py

Enhanced logging to both console and pipeline_logs/pipeline_6710.log
"""
import json, logging, os, sys, time, datetime
import httpx

BASE = "http://127.0.0.1:18081"
BOOKS = [6, 7, 9, 10]
LOG_DIR = "pipeline_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Log file name with timestamp
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"pipeline_6710_{TIMESTAMP}.log")

# Configure logging: file + console
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger()

# Also write a symlink-like latest log reference
LATEST_LINK = os.path.join(LOG_DIR, "pipeline_6710_latest.log")
try:
    if os.path.exists(LATEST_LINK):
        os.remove(LATEST_LINK)
except:
    pass

# Phase definitions: (phase_num, description, url_template, body, timeout_seconds, skip)
# skip=True means log a warning and move on without calling
PHASES = [
    (3, "Extract (llama-server via tunnel)", "/api/books/{}/extract", {"use_model": True}, 43200, False),
    (4, "Entity Governance", "/api/books/{}/govern", {}, 600, False),
    (5, "Narrative Build", "/api/books/{}/narrative", {}, 600, False),
    (6, "Index Qdrant (SKIPPED - remote only, no local embedding model)", None, None, 0, True),
    (7, "Graph Project (Neo4j)", "/api/books/{}/graph/project", {}, 600, False),
    (8, "Export ChapterFacts (training samples)", "/api/eval/export/chapter-facts?book_id={}&min_review=PENDING", {}, 300, False),
]


def call_api(path, body=None, timeout=600, label="", retries=2):
    """POST to rag-agent API with retry on transient failures"""
    url = f"{BASE}{path}"
    last_error = None
    for attempt in range(1 + retries):
        try:
            log.info(f"  [{label}] >>> POST {path} (attempt {attempt+1}, timeout={timeout}s)")
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=body or {})
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "")
                preview = json.dumps(data, ensure_ascii=False)[:500]
                if status in ("success", "ok"):
                    log.info(f"  [{label}] <<< OK ({resp.status_code}): {preview}")
                else:
                    log.warning(f"  [{label}] <<< WARN status={status} ({resp.status_code}): {preview}")
                return data
        except httpx.TimeoutException as e:
            last_error = e
            log.warning(f"  [{label}] <<< TIMEOUT (attempt {attempt+1}): {e}")
            if attempt < retries:
                wait = 30
                log.info(f"  [{label}] --- waiting {wait}s before retry ---")
                time.sleep(wait)
        except httpx.ConnectError as e:
            last_error = e
            log.error(f"  [{label}] <<< CONNECT ERROR (attempt {attempt+1}): {e}")
            if attempt < retries:
                wait = 10
                log.info(f"  [{label}] --- waiting {wait}s before retry ---")
                time.sleep(wait)
        except Exception as e:
            last_error = e
            log.error(f"  [{label}] <<< FAILED (attempt {attempt+1}): {e}")
            if attempt < retries:
                wait = 5
                log.info(f"  [{label}] --- waiting {wait}s before retry ---")
                time.sleep(wait)
    # All retries exhausted
    raise last_error if last_error else RuntimeError(f"{label}: failed after {retries+1} attempts")


def check_health():
    """Verify rag-agent is reachable before starting"""
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(f"{BASE}/health")
            resp.raise_for_status()
            data = resp.json()
            log.info(f"  RAG-agent health: {json.dumps(data, ensure_ascii=False)[:200]}")
            return True
    except Exception as e:
        log.error(f"  RAG-agent health check FAILED: {e}")
        return False


def run_phase_for_book(pn, desc, tmpl, body, timeout, skip, book_id):
    """Run a single phase for a single book"""
    label = f"B{book_id}/P{pn}"
    if skip:
        log.info(f"  [{label}] --- SKIPPED ({desc}) ---")
        return {"status": "skipped", "note": desc}
    path = tmpl.format(book_id)
    return call_api(path, body=body, timeout=timeout, label=label)


def main():
    """Orchestrate the full pipeline"""
    start_time = datetime.datetime.now()
    log.info(f"{'='*70}")
    log.info(f"PIPELINE 6-7-9-10 START at {start_time}")
    log.info(f"{'='*70}")
    log.info(f"  Target: {BASE}")
    log.info(f"  Books: {BOOKS}")
    log.info(f"  Log file: {LOG_FILE}")
    log.info(f"{'='*70}")

    # Health check
    if not check_health():
        log.error("RAG-agent unreachable. Aborting pipeline.")
        sys.exit(1)

    # Phase-by-phase, book-by-book
    results = {}  # results[book_id] = {phase_num: status}
    for book_id in BOOKS:
        results[book_id] = {}

    for pn, desc, tmpl, body, timeout, skip in PHASES:
        phase_start = time.time()
        log.info(f"\n{'='*70}")
        log.info(f"PHASE {pn}: {desc}")
        log.info(f"{'='*70}")

        for book_id in BOOKS:
            book_start = time.time()
            log.info(f"\n--- Book {book_id} - {desc} ---")
            try:
                data = run_phase_for_book(pn, desc, tmpl, body, timeout, skip, book_id)
                results[book_id][pn] = data.get("status", "unknown")
                elapsed = time.time() - book_start
                log.info(f"[B{book_id}/P{pn}] Completed in {elapsed:.1f}s with status={data.get('status','?')}")
            except Exception as e:
                elapsed = time.time() - book_start
                if pn == 3:
                    log.error(f"[B{book_id}/P{pn}] EXTRACT FAILED after {elapsed:.1f}s - aborting rest of book {book_id}")
                    results[book_id][pn] = "failed"
                    # Abort remaining phases for this book
                    for later_pn, later_desc, _, _, _, later_skip in PHASES:
                        if later_pn > pn:
                            results[book_id][later_pn] = "aborted"
                            log.info(f"[B{book_id}/P{later_pn}] Aborted (due to Phase 3 failure)")
                    break
                else:
                    log.warning(f"[B{book_id}/P{pn}] FAILED after {elapsed:.1f}s - {e}")
                    results[book_id][pn] = "failed"

        phase_elapsed = time.time() - phase_start
        log.info(f"\n  Phase {pn} total time: {phase_elapsed:.1f}s")

    # Summary
    total_elapsed = time.time() - start_time
    log.info(f"\n{'='*70}")
    log.info(f"PIPELINE 6-7-9-10 COMPLETE")
    log.info(f"{'='*70}")
    log.info(f"  Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
    log.info(f"  Log file: {LOG_FILE}")
    log.info(f"\n  Results by book:")
    for book_id in BOOKS:
        phases_run = [f"P{pn}={st}" for pn, st in sorted(results[book_id].items())]
        log.info(f"    Book {book_id}: {', '.join(phases_run) if phases_run else 'nothing run'}")

    log.info(f"\n  IMPORTANT: Phase 6 (index) was SKIPPED.")
    log.info(f"  Run on remote server after pipeline completes:")
    log.info(f"    For each book_id in {BOOKS}:")
    log.info(f"      SSH to remote, conda activate llamacpp, cd apps/rag-agent")
    log.info(f"      python -c \"from app.runners.index_runner import index_book; import asyncio; asyncio.run(index_book({book_id}, reindex=True))\"")
    log.info(f"{'='*70}")

    # Write final summary to a separate file
    summary_file = os.path.join(LOG_DIR, f"pipeline_6710_summary_{TIMESTAMP}.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "books": BOOKS,
            "start_time": start_time.isoformat(),
            "end_time": datetime.datetime.now().isoformat(),
            "total_seconds": total_elapsed,
            "results": {str(b): results[b] for b in BOOKS},
            "log_file": LOG_FILE,
            "note": "Phase 6 (index) skipped - run on remote server"
        }, f, ensure_ascii=False, indent=2)
    log.info(f"  Summary written to {summary_file}")

    # Generate log index entry
    log_index = os.path.join(LOG_DIR, "pipeline_index.json")
    try:
        if os.path.exists(log_index):
            with open(log_index, "r", encoding="utf-8") as f:
                index = json.load(f)
        else:
            index = []
    except:
        index = []
    index.append({
        "run_id": TIMESTAMP,
        "books": BOOKS,
        "start": start_time.isoformat(),
        "end": datetime.datetime.now().isoformat(),
        "log": LOG_FILE,
        "summary": summary_file
    })
    with open(log_index, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # Copy to latest log reference
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as src:
            content = src.read()
        with open(LATEST_LINK, "w", encoding="utf-8") as dst:
            dst.write(content)
    except:
        pass


if __name__ == "__main__":
    main()
