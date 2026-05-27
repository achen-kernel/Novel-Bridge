"""Fix P5 + P8 - pass MysqlClient, not Connection"""
import sys, os, json
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
from app.pipeline.narrative_builder import NarrativeBuilder
from app.stores.chapter_fact_store import ChapterFactStore
from datetime import datetime

db = MysqlClient()
BOOKS = [(6,"西游记"),(7,"聊斋志异"),(8,"搜神记"),(9,"山海经"),(10,"水浒传")]

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

for bid, bname in BOOKS:
    # P5: pass MysqlClient instance
    print(f"P5 {bname}...", end=" ", flush=True)
    try:
        r = NarrativeBuilder(db).build_from_book(bid)
        print(f"OK", flush=True)
    except Exception as e:
        print(f"FAIL: {e}", flush=True)

    # P8: use custom JSON encoder for datetime
    print(f"P8 {bname}...", end=" ", flush=True)
    try:
        conn = db.connect()
        facts = ChapterFactStore(conn).find_by_book(bid)
        out = f"training/data/chapter_facts_book_{bid}.jsonl"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            for fact in facts:
                # Remove non-serializable fields
                clean = {k: v for k, v in fact.items() if not isinstance(v, (datetime,))}
                f.write(json.dumps(clean, ensure_ascii=False, cls=DateTimeEncoder) + "\n")
        print(f"{len(facts)} facts", flush=True)
    except Exception as e:
        print(f"FAIL: {e}", flush=True)

print("Done!")
