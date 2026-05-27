"""Deep debug: trace retrieval at each step via MySQL"""
import json
import os
import pymysql

conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''),
    database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

questions = [
    (6, '孙悟空的金箍棒是从哪里来的？'),
    (6, '猪八戒为什么被贬下凡间？'),
    (6, '唐僧有哪些徒弟？分别是谁？'),
    (10, '武松打虎的故事发生在哪里？'),
    (7, '聂小倩是什么身份？'),
]

for book_id, question in questions:
    print(f"\n{'='*60}")
    print(f"Book {book_id} | Q: {question}")
    print('='*60)
    
    # Extract keywords same way as retrieval_runner
    import re
    stopwords = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
        "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
        "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她",
        "它", "们", "那", "什么", "怎么", "为什么", "如何", "请问",
        "吗", "啊", "呢", "吧", "呀", "哦", "嗯",
    }
    tokens = re.findall(r'[\u4e00-\u9fff]{2,6}', question)
    keywords = [t for t in tokens if t not in stopwords and len(t) >= 2]
    keywords = list(set(keywords))
    print(f"  Keywords: {keywords}")
    
    # Check lexical: count chunks matching each keyword
    with conn.cursor() as cursor:
        for kw in keywords:
            pattern = f'%{kw}%'
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM novel_chunk WHERE book_id = %s AND content LIKE %s",
                (book_id, pattern)
            )
            row = cursor.fetchone()
            cnt = row['cnt']
            print(f"  LIKE '%{kw}%': {cnt} chunks")
            
            if cnt > 0:
                cursor.execute(
                    "SELECT id, content FROM novel_chunk WHERE book_id = %s AND content LIKE %s LIMIT 1",
                    (book_id, pattern)
                )
                row = cursor.fetchone()
                if row:
                    snippet = row['content'][:200].replace('\n', ' ')
                    print(f"    chunk #{row['id']}: {snippet}...")
    
    # Check chapter facts
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM novel_chapter_fact WHERE book_id = %s",
            (book_id,)
        )
        row = cursor.fetchone()
        fact_cnt = row['cnt']
        print(f"  ChapterFacts: {fact_cnt} total")
        
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM novel_chapter_fact WHERE book_id = %s AND (summary IS NOT NULL AND summary != '')",
            (book_id,)
        )
        row = cursor.fetchone()
        has_summary = row['cnt']
        print(f"  ChapterFacts with summary: {has_summary}")
        
        cursor.execute(
            "SELECT id, chapter_id, fact_json FROM novel_chapter_fact WHERE book_id = %s LIMIT 2",
            (book_id,)
        )
        for row in cursor.fetchall():
            try:
                fj = json.loads(row['fact_json']) if row['fact_json'] else {}
                events = fj.get('events', [])
                entities = fj.get('entities', [])
                print(f"  Fact #{row['id']} (ch. {row['chapter_id']}): "
                      f"{len(entities)} entities, {len(events)} events")
                if events:
                    e = events[0]
                    print(f"    First event: desc={e.get('description','')[:80]}")
                    print(f"    First event: summary={e.get('summary','')[:80]}")
            except:
                pass
    
    # Check Qdrant stats
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM novel_chunk WHERE book_id = %s AND vector_id IS NOT NULL",
            (book_id,)
        )
        row = cursor.fetchone()
        indexed = row['cnt']
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM novel_chunk WHERE book_id = %s",
            (book_id,)
        )
        total_chunks = cursor.fetchone()['cnt']
        print(f"  Chunks indexed in Qdrant: {indexed}/{total_chunks}")

conn.close()
