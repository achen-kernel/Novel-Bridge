"""Debug: check if descriptions are in the profiles dict before insert"""
import pymysql, sys, json, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.pipeline.entity_governance_runner import EntityGovernanceRunner
from app.clients.mysql_client import MysqlClient

# Check directly: does fact_json have descriptions with display_name 娌欐偀鍑€?
conn = pymysql.connect(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''), database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as c:
    # Get a fact_json, extract characters with descriptions
    c.execute("""
        SELECT fact_json FROM novel_chapter_fact 
        WHERE book_id = 6 AND fact_json LIKE '%娌欐偀鍑€%' 
        LIMIT 1
    """)
    row = c.fetchone()
    if row:
        fj = json.loads(row['fact_json']) if isinstance(row['fact_json'], str) else row['fact_json']
        chars = fj.get('characters', [])
        print(f'Characters with description in fact_json:')
        for ch in chars:
            desc = ch.get('description', '')
            print(f'  {ch.get("display_name","?")}: desc={desc[:60] if desc else "EMPTY"}')

# Check current entity_profile descriptions
with conn.cursor() as c:
    c.execute("SELECT COUNT(*) as total, SUM(CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END) as has_desc FROM novel_entity_profile WHERE book_id = 6")
    row = c.fetchone()
    print(f'\nEntity profiles: {row["total"]} total, {row["has_desc"]} with description')

# Check specifically for 娌欐偀鍑€
with conn.cursor() as c:
    c.execute("SELECT canonical_name, LEFT(description,100) as desc_short FROM novel_entity_profile WHERE book_id = 6 AND canonical_name LIKE '%娌?'")
    for r in c.fetchall():
        print(f'  {r["canonical_name"]}: desc={r["desc_short"][:60] if r["desc_short"] else "EMPTY"}')

conn.close()

