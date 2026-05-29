"""
Batch pipeline runner. Triggers fullPipeline P1-P8 for given books.
Usage: python _run_books.py [book_id ...]
   eg: python _run_books.py 8 9 7 6 10
"""
import asyncio, json, sys, time
import httpx

BASE = "http://127.0.0.1:18079"
PHASES = ['P1','P2','P3','P4','P5','P6','P7','P8']

async def wait_task(client, task_id, phase, book_id, timeout=3600):
    t0 = time.time()
    for i in range(timeout // 3):
        await asyncio.sleep(3)
        try:
            r = await client.get(f"{BASE}/api/v2/tasks/{task_id}")
            t = r.json()
            elapsed = time.time() - t0
            if t['status'] == 'SUCCESS':
                print(f"  ✅ {phase} 成功 ({elapsed:.0f}s)  msg={t.get('message','')[:80]}")
                return True
            elif t['status'] == 'FAILED':
                print(f"  ❌ {phase} 失败 ({elapsed:.0f}s): {t.get('error','')[:200]}")
                return False
            elif i % 20 == 0:
                print(f"  ⏳ {phase} {t['status']} progress={t['progress']} msg={t.get('message','')[:60]} ({elapsed:.0f}s)")
        except Exception as e:
            print(f"  ⚠ wait_task error: {e}")
    print(f"  ⌛ {phase} 超时")
    return False

# P3 提取非常慢（每章调模型），给 3 小时超时
P3_TIMEOUT = 10800  # 3 hours

async def run_book(client, book_id, title):
    print(f"\n{'='*50}")
    print(f" 开始处理: {title} (book {book_id})")
    print(f"{'='*50}")
    
    # 1. Cleanup
    print(" 清理旧数据...")
    for ep in ['', '/qdrant', '/neo4j']:
        r = await client.post(f"{BASE}/api/v2/books/{book_id}/cleanup{ep}")
        if r.json().get('status') != 'success':
            print(f"  清理失败: {ep}")
            return False
    
    # 2. Run each phase
    for phase in PHASES:
        print(f"\n 触发 {phase}...")
        try:
            # Use model=True, provider="local" for all phases
            r = await client.post(
                f"{BASE}/api/v2/books/{book_id}/phase/{phase}",
                json={"use_model": True, "provider": "local"}
            )
            data = r.json()
            if data.get('status') == 'started':
                timeout = P3_TIMEOUT if phase == 'P3' else 3600
                ok = await wait_task(client, data['task_id'], phase, book_id, timeout)
                if not ok:
                    print(f"  ⛔ {phase} 失败，终止本书")
                    return False
            else:
                print(f"  ❌ 触发失败: {data}")
                return False
        except Exception as e:
            print(f"  ❌ 异常: {e}")
            return False
    
    print(f"\n✅ {title} 全流程完成！")
    return True

async def main():
    books = {6: "西游记", 7: "聊斋志异", 8: "搜神记", 9: "山海经", 10: "水浒传"}
    
    if len(sys.argv) > 1:
        ids = [int(a) for a in sys.argv[1:]]
    else:
        ids = [8, 9, 7, 6, 10]  # default: small first
    
    async with httpx.AsyncClient(timeout=30) as client:
        for bid in ids:
            if bid not in books:
                print(f"跳过未知 book_id={bid}")
                continue
            ok = await run_book(client, bid, books[bid])
            if not ok:
                print(f"⛔ {books[bid]} 失败，继续下一本...")
            # Small delay between books
            await asyncio.sleep(2)

asyncio.run(main())
print("\n全部完成！")
