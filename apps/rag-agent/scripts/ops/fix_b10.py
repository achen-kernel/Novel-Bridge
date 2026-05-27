"""Fix remaining Book 10 entity name mismatches"""
import pymysql, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.quality.stages.entity_name_normalizer import EntityNameNormalizer
conn = pymysql.connect(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''), database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
normalizer = EntityNameNormalizer(conn)
r = normalizer.run(book_id=10, dry_run=False)
print(f'Updated: {r["stats"]["updated"]}')
conn.close()

