"""
Direct pipeline execution — calls pipeline modules directly, no HTTP.
No server needed, no timeouts, no browser.
"""
import sys, os, time, json, pymysql

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ["APP_ENV"] = "local"

# Load .env from rag-agent directory
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from app.clients.mysql_client import MysqlClient
from app.pipeline.book_processor import BookProcessor
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

def rowcount(conn, table, bid):
    with conn.cursor() as c:
        c.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE book_id=%s", (bid,))
        r = c.fetchone()
        return r["cnt"] if r else 0

for bid, bname in BOOKS:
    log(f"\n{'='*50}")
    log(f"  {bname}({bid})")
    log(f"{'='*50}")
    
    # P1: Split + Chunk
    sys.stdout.write("  P1 分章... ")
    sys.stdout.flush()
    t0 = time.time()
    try:
        p = BookProcessor(db)
        r = p.process(bid, 0)
        log(f"OK ({time.time()-t0:.0f}s) chaps={r.get('chapters','?')} chunks={r.get('chunks','?')}")
    except Exception as e:
        log(f"FAIL: {e}")
    
    # P2: Prior Hint (DeepSeek)
    log("  P2 梗概...")
    t0 = time.time()
    try:
        conn = db.connect()
        with conn.cursor() as c:
            c.execute("SELECT id, title, raw_text FROM novel_book WHERE id=%s", (bid,))
            book = c.fetchone()
            hint_text = book["raw_text"][:12000] if book else ""
            book_title = book["title"] if book else ""
        
        import asyncio
        from app.clients.deepseek_client import deepseek_client
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "..", "app", "prompts", "book_prior_hint.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
        prompt = prompt_template.replace("{book_title}", book_title).replace("{raw_text}", hint_text)
        
        result = asyncio.run(deepseek_client.chat_json([
            {"role": "system", "content": "你是古典小说分析专家。"},
            {"role": "user", "content": prompt},
        ]))
        prior_hint = result if isinstance(result, dict) else {"raw": result}
        with conn.cursor() as c:
            c.execute("UPDATE novel_book SET prior_hint_json=%s WHERE id=%s",
                      (json.dumps(prior_hint, ensure_ascii=False), bid))
        conn.commit()
        log(f"OK ({time.time()-t0:.0f}s)")
    except Exception as e:
        log(f"FAIL: {e}")
        conn = db.connect()  # reconnect if broken
    
    # P3: Extract (rule-based for speed)
    log("  P3 提取...")
    t0 = time.time()
    try:
        conn = db.connect()
        # Check existing
        existing = rowcount(conn, "novel_chapter_fact", bid)
        chaps = rowcount(conn, "novel_chunk", bid)
        if existing >= chaps:
            log(f"SKIP (already {existing}/{chaps})")
        else:
            runner = FactPipelineRunner(db, use_model=False)
            r = asyncio.run(runner.process_book(bid))
            done = rowcount(db.connect(), "novel_chapter_fact", bid)
            log(f"OK ({time.time()-t0:.0f}s) facts={done}")
    except Exception as e:
        log(f"FAIL: {e}")
    
    # P4: Govern
    log("  P4 治理...")
    t0 = time.time()
    try:
        conn = db.connect()
        runner = EntityGovernanceRunner(db)
        r = runner.process_book(bid)
        log(f"OK ({time.time()-t0:.0f}s) profiles={r.get('profiles',0)}")
    except Exception as e:
        log(f"FAIL: {e}")
    
    # P5: Narrative
    log("  P5 叙事...")
    t0 = time.time()
    try:
        conn = db.connect()
        builder = NarrativeBuilder(conn)
        r = builder.build_from_book(bid)
        log(f"OK ({time.time()-t0:.0f}s)")
    except Exception as e:
        log(f"FAIL: {e}")
    
    # P6: Index (Qdrant reindex)
    log("  P6 索引...")
    t0 = time.time()
    try:
        runner = IndexRunner(db)
        r = asyncio.run(runner.index_book(bid, reindex=True))
        log(f"OK ({time.time()-t0:.0f}s) chunks={r.get('chunks_indexed',0)}")
    except Exception as e:
        log(f"FAIL: {e}")
    
    # P7: Neo4j
    log("  P7 图谱...")
    t0 = time.time()
    try:
        conn = db.connect()
        projector = GraphProjector(conn)
        r = projector.project_book(bid, clear_first=True)
        log(f"OK ({time.time()-t0:.0f}s) entities={r.get('entities',0)}")
    except Exception as e:
        log(f"FAIL: {e}")
    
    # P8: Export
    log("  P8 导出...")
    t0 = time.time()
    try:
        conn = db.connect()
        store = ChapterFactStore(conn)
        facts = store.find_by_book(bid)
        out = f"training/data/chapter_facts_book_{bid}.jsonl"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            for fact in facts:
                f.write(json.dumps(fact, ensure_ascii=False) + "\n")
        log(f"OK ({time.time()-t0:.0f}s) {len(facts)} facts -> {out}")
    except Exception as e:
        log(f"FAIL: {e}")

log(f"\n{'='*50}")
log("  All done!")
log(f"{'='*50}")
log("  Results:")
conn = db.connect()
for bid, bname in BOOKS:
    chaps = rowcount(conn, "novel_chapter", bid)
    chunks = rowcount(conn, "novel_chunk", bid)
    facts = rowcount(conn, "novel_chapter_fact", bid)
    profiles = rowcount(conn, "novel_entity_profile", bid)
    log(f"  {bname}: {chaps}ch {chunks}ck {facts}facts {profiles}profiles")
