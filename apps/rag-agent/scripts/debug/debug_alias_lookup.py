"""Debug: check if alias lookup works for 娌欏儳"""
import json, pymysql, sys
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
conn = pymysql.connect(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''), database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

question = '娌欏儳鍦ㄨ璐箣鍓嶆槸浠€涔堣韩浠斤紵'
book_id = 6

# Simulate _entity_chunk_lookup with alias matching
with conn.cursor() as c:
    c.execute(
        "SELECT canonical_name, aliases_json FROM novel_entity_profile "
        "WHERE book_id = %s AND status = 'ACTIVE' AND LENGTH(canonical_name) >= 2",
        (book_id,)
    )
    matched = set()
    for row in c.fetchall():
        name = row['canonical_name']
        if name in question:
            matched.add(name)
            continue
        try:
            aliases = json.loads(row['aliases_json']) if row.get('aliases_json') else []
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str) and len(alias) >= 2 and alias in question:
                        matched.add(name)
                        print(f'  Alias match: "{alias}" -> canonical "{name}"')
                        break
        except Exception:
            pass
    print(f'Matched canonical names: {matched}')

# Simulate knowledge_search keyword extraction
import re
stopwords = {'鐨?,'浜?,'鍦?,'鏄?,'鎴?,'鏈?,'鍜?,'灏?,'涓?,'浜?,'閮?,'涓€','涓€涓?,'涓?,'涔?,'寰?,'鍒?,'璇?,'瑕?,'鍘?,'浣?,'浼?,'鐫€','娌℃湁','鐪?,'濂?,'鑷繁','杩?,'浠?,'濂?,'瀹?,'浠?,'閭?,'浠€涔?,'鎬庝箞','涓轰粈涔?,'濡備綍','璇烽棶','鍚?,'鍟?,'鍛?,'鍚?,'鍛€','鍝?,'鍡?}
tokens = re.findall(r'[\u4e00-\u9fff]+', question)
keywords = set()
for seg in tokens:
    for n in range(2, min(5, len(seg)+1)):
        for i in range(len(seg)-n+1):
            g = seg[i:i+n]
            if g not in stopwords:
                keywords.add(g)
keywords = sorted(keywords, key=lambda x: (len(x), x))[:20]
print(f'Keywords: {keywords}')

# Check if aliases_json LIKE '%娌欏儳%' works
with conn.cursor() as c:
    c.execute("SELECT canonical_name FROM novel_entity_profile WHERE book_id = %s AND aliases_json LIKE %s LIMIT 5",
              (book_id, '%娌欏儳%'))
    rows = c.fetchall()
    print(f'aliases_json LIKE "%%娌欏儳%%": {[r["canonical_name"] for r in rows]}')

conn.close()

