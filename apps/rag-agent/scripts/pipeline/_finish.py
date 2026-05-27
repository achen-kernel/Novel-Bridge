"""Continue pipeline - run P5-P8 for all books, P3-P4 for unfinished."""
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

for bid, bname in BOOKS:
    log(f"\n  === {bname}({bid}) ===")
    conn = db.connect()
    chaps = rc(conn, "novel_chapter", bid)
    chunks = rc(conn, "novel_chunk", bid)
    facts = rc(conn, "novel_chapter_fact", bid)
    log(f"  State: {chaps}ch {chunks}ck {facts}facts")

    # P3 if needed
    if facts < chaps and chaps > 0:
        log("  P3 extract start")
        t0 = time.time()
        try:
            asyncio.run(FactPipelineRunner(db, use_model=False).process_book(bid))
            done = rc(db.connect(), "novel_chapter_fact", bid)
            log(f"  P3 done: {done}facts ({time.time()-t0:.0f}s)")
        except Exception as e:
            log(f"  P3 FAIL: {e}")

    # P4 if needed
    profiles = rc(conn, "novel_entity_profile", bid)
    if profiles == 0 and rc(conn, "novel_chapter_fact", bid) > 0:
        log("  P4 govern start")
        t0 = time.time()
        try:
            r = EntityGovernanceRunner(db).process_book(bid)
            log(f"  P4 done: {r.get('profiles',0)}profiles ({time.time()-t0:.0f}s)")
        except Exception as e:
            log(f"  P4 FAIL: {e}")

    # P5-P8 always run
    for phase_name, phase_fn in [
        ("P5 narrative", lambda: NarrativeBuilder(db.connect()).build_from_book(bid)),
        ("P6 index", lambda: asyncio.run(IndexRunner(db).index_book(bid, reindex=True))),
        ("P7 graph", lambda: GraphProjector(db.connect()).project_book(bid, clear_first=True)),
        ("P8 export", lambda: _export(bid)),
    ]:
        log(f"  {phase_name} start")
        t0 = time.time()
        try:
            phase_fn()
            log(f"  {phase_name} done ({time.time()-t0:.0f}s)")
        except Exception as e:
            log(f"  {phase_name} FAIL: {e}")

def _export(bid):
    facts_data = ChapterFactStore(db.connect()).find_by_book(bid)
    out = f"training/data/chapter_facts_book_{bid}.jsonl"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for fact in facts_data:
            f.write(json.dumps(fact, ensure_ascii=False) + "\n")
    log(f"  exported {len(facts_data)} facts")

log(f"\n  === FINAL REPORT ===")
conn = db.connect()
for bid, bname in BOOKS:
    log(f"  {bname}: ch={rc(conn,'novel_chapter',bid)} ck={rc(conn,'novel_chunk',bid)} facts={rc(conn,'novel_chapter_fact',bid)} profiles={rc(conn,'novel_entity_profile',bid)}")
