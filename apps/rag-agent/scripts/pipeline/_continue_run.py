"""Continue pipeline for remaining books."""
import sys, os, time, json, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from app.clients.mysql_client import MysqlClient
from app.pipeline.fact_pipeline_runner import FactPipelineRunner
from app.pipeline.entity_governance_runner import EntityGovernanceRunner
from app.pipeline.narrative_builder import NarrativeBuilder
from app.pipeline.index_runner import IndexRunner
from app.pipeline.graph_projector import GraphProjector
from app.stores.chapter_fact_store import ChapterFactStore

db = MysqlClient()
BOOKS = [(6,"西游记"),(7,"聊斋志异"),(8,"搜神记"),(9,"山海经"),(10,"水浒传")]

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def rc(conn, table, bid):
    with conn.cursor() as c:
        c.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE book_id=%s", (bid,))
        r = c.fetchone()
        return r["cnt"] if r else 0

def need_phase(conn, bid, table, expected):
    """Check if this phase is already done."""
    return rc(conn, table, bid) < expected

for bid, bname in BOOKS:
    log(f"\n  === {bname}({bid}) ===")
    conn = db.connect()
    chaps = rc(conn, "novel_chapter", bid)
    chunks = rc(conn, "novel_chunk", bid)
    facts = rc(conn, "novel_chapter_fact", bid)
    log(f"  Current: {chaps}ch {chunks}ck {facts}facts")
    
    # P3
    if facts < chaps and chaps > 0:
        log("  P3 提取...", end="")
        t0 = time.time()
        try:
            r = asyncio.run(FactPipelineRunner(db, use_model=False).process_book(bid))
            done = rc(db.connect(), "novel_chapter_fact", bid)
            log(f" {done}facts ({time.time()-t0:.0f}s)")
        except Exception as e:
            log(f" FAIL: {e}")
    
    # P4
    profiles = rc(conn, "novel_entity_profile", bid)
    if profiles == 0 and facts > 0:
        log("  P4 治理...", end="")
        t0 = time.time()
        try:
            r = EntityGovernanceRunner(db).process_book(bid)
            log(f" {r.get('profiles',0)}profiles ({time.time()-t0:.0f}s)")
        except Exception as e:
            log(f" FAIL: {e}")
    
    # P5
    log("  P5 叙事...", end="")
    t0 = time.time()
    try:
        r = NarrativeBuilder(db.connect()).build_from_book(bid)
        log(f" ({time.time()-t0:.0f}s)")
    except Exception as e:
        log(f" FAIL: {e}")
    
    # P6
    log("  P6 索引...", end="")
    t0 = time.time()
    try:
        r = asyncio.run(IndexRunner(db).index_book(bid, reindex=True))
        log(f" ({time.time()-t0:.0f}s)")
    except Exception as e:
        log(f" FAIL: {e}")
    
    # P7
    log("  P7 图谱...", end="")
    t0 = time.time()
    try:
        r = GraphProjector(db.connect()).project_book(bid, clear_first=True)
        log(f" ({time.time()-t0:.0f}s)")
    except Exception as e:
        log(f" FAIL: {e}")
    
    # P8
    log("  P8 导出...", end="")
    t0 = time.time()
    try:
        facts_data = ChapterFactStore(db.connect()).find_by_book(bid)
        out = f"training/data/chapter_facts_book_{bid}.jsonl"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            for fact in facts_data:
                f.write(json.dumps(fact, ensure_ascii=False) + "\n")
        log(f" {len(facts_data)}facts ({time.time()-t0:.0f}s)")
    except Exception as e:
        log(f" FAIL: {e}")

log(f"\n{'='*40}")
log("  ALL DONE!")
conn = db.connect()
for bid, bname in BOOKS:
    ch = rc(conn, "novel_chapter", bid)
    ck = rc(conn, "novel_chunk", bid)
    cf = rc(conn, "novel_chapter_fact", bid)
    ep = rc(conn, "novel_entity_profile", bid)
    log(f"  {bname}: {ch}ch {ck}ck {cf}facts {ep}profiles")
