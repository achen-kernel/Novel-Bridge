"""
Super simple pipeline runner - port 18084
Order: 8, 7
"""
import json, logging, os, sys, time
import httpx

BASE = "http://127.0.0.1:18084"
BOOKS = [8, 7]
LOG_DIR = "pipeline_logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(os.path.join(LOG_DIR, "pipeline.log"), encoding="utf-8"), logging.StreamHandler(sys.stdout)])
log = logging.getLogger()

def call(path, body=None, timeout=600, label=""):
    url = f"{BASE}{path}"
    log.info(f"  >>> {label or path}")
    try:
        with httpx.Client(timeout=timeout) as c:
            r = c.post(url, json=body or {})
            r.raise_for_status()
            d = r.json()
            s = d.get("status","")
            p = json.dumps(d, ensure_ascii=False)[:200]
            log.info(f"  {'<<< OK' if s in ('success','ok') else '<<< WARN'}: {p}")
            return d
    except Exception as e:
        log.error(f"  <<< FAILED: {e}")
        raise

phases = [
    (3, "Extract (llama-server)", "/api/books/{}/extract", {"use_model": True}, 43200),
    (4, "Entity Governance", "/api/books/{}/govern", {}, 600),
    (5, "Narrative Build", "/api/books/{}/narrative", {}, 600),
    (6, "Index Qdrant", "/api/books/{}/index", {"reindex": True}, 600),
    (7, "Graph Project", "/api/books/{}/graph/project", {}, 600),
    (8, "Export ChapterFacts (training samples)", "/api/eval/export/chapter-facts?book_id={}&min_review=PENDING", {}, 300),
]

for pn, desc, tmpl, body, to in phases:
    log.info(f"\n{'='*60}")
    log.info(f"PHASE {pn}: {desc}")
    log.info(f"{'='*60}")
    for b in BOOKS:
        log.info(f"--- Book {b} {desc} ---")
        try:
            call(tmpl.format(b), body, timeout=to, label=f"Book {b}")
        except Exception as e:
            if pn == 3:
                log.error(f"  Book {b} extract FAILED - aborting rest of book")
                break
            else:
                log.warning(f"  Book {b} skipped: {e}")

log.info(f"\n{'='*60}")
log.info("ALL DONE!")
log.info(f"{'='*60}")
