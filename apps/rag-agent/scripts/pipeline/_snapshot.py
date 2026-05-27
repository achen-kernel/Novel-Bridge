import os, pymysql
c = pymysql.connect(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''), database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'))
with c.cursor() as cur:
    print('=== 数据汇总 ===')
    for bid,n in [(6,'西游记'),(7,'聊斋'),(8,'搜神记'),(9,'山海经'),(10,'水浒传')]:
        cur.execute('SELECT status, chapter_count, chunk_count FROM novel_book WHERE id=%s', (bid,))
        bk = cur.fetchone()
        cur.execute('SELECT COUNT(*) FROM novel_chapter WHERE book_id=%s', (bid,))
        ch = cur.fetchone()['COUNT(*)']
        cur.execute('SELECT COUNT(*) FROM novel_chunk WHERE book_id=%s', (bid,))
        ck = cur.fetchone()['COUNT(*)']
        cur.execute('SELECT COUNT(*) FROM novel_chapter_fact WHERE book_id=%s', (bid,))
        cf = cur.fetchone()['COUNT(*)']
        cur.execute('SELECT COUNT(*) FROM novel_entity_profile WHERE book_id=%s', (bid,))
        ep = cur.fetchone()['COUNT(*)']
        cur.execute('SELECT COUNT(*) FROM novel_relation_fact WHERE book_id=%s', (bid,))
        rf = cur.fetchone()['COUNT(*)']
        cur.execute('SELECT COUNT(*) FROM novel_event_fact WHERE book_id=%s', (bid,))
        ef = cur.fetchone()['COUNT(*)']
        cur.execute('SELECT COUNT(*) FROM novel_relation_mention WHERE book_id=%s', (bid,))
        rm = cur.fetchone()['COUNT(*)']
        cur.execute('SELECT COUNT(*) FROM novel_event_mention WHERE book_id=%s', (bid,))
        em = cur.fetchone()['COUNT(*)']
        cur.execute('SELECT prior_hint_json IS NOT NULL as has_hint FROM novel_book WHERE id=%s', (bid,))
        p2 = cur.fetchone()['has_hint']
        print(f'{n}({bid}): P1={ch}ch/{ck}ck P2={"Y" if p2 else "-"} P3={cf}facts P4={ep}profiles P5={rf}r+{ef}e+{rm}rm+{em}em')
c.close()
print()
print('=== 文件改动清单 ===')
print('apps/rag-agent/app/pipeline/chunker.py - CRLF修复+文言文自适应分块')
print('apps/rag-agent/app/pipeline/extraction_runner.py - 规则回退加关系/事件提取')
print('apps/rag-agent/app/pipeline/graph_projector.py - Neo4j书级清除')
print('apps/rag-agent/app/clients/neo4j_client.py - 加book_id属性+clear_book')
print('apps/rag-agent/app/pipeline/task_manager.py - 后台任务管理器+取消')
print('apps/rag-agent/app/api/pipeline_v2.py - 流水线API v2+背景任务+清理')
print('apps/rag-agent/app/api/frontend.py - 流水线前端页面')
print('apps/rag-agent/app/api/demo.py - 导航加流水线链接+项目删除')
print('apps/rag-agent/app/main.py - 注册pipeline_v2路由')
print('apps/rag-agent/app/stores/chapter_fact_store.py - 去掉ORDER BY排序')
print('apps/rag-agent/scripts/pipeline/re_run_all_books.py - 全量重跑脚本')
print('apps/rag-agent/scripts/pipeline/_trigger_all.py - 全触发脚本')
print('apps/rag-agent/scripts/pipeline/_direct_run.py - 直接管线脚本')
print('apps/rag-agent/scripts/pipeline/_finish.py - 续跑脚本')
print('apps/rag-agent/scripts/start_server.py - 服务启动脚本')
print('docs/learn/retro-log.md - 更新踩坑记录')
print('docs/简历梳理.md - 更新面试问答')
