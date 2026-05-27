"""Create eval cases and run eval"""
import os, pymysql, httpx, json

DB = dict(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user="novel_bridge",
          password=os.environ.get('MYSQL_PASSWORD', ''), db=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset="utf8mb4")

# Check existing cases
conn = pymysql.connect(**DB)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM novel_eval_case")
count = c.fetchone()[0]
print(f"Existing eval cases: {count}")

if count == 0:
    print("Creating eval cases...")
    cases = [
        (6, "孙悟空有哪些主要特征？", "CHARACTER", "EASY"),
        (6, "唐僧取经路上经历了哪些磨难？", "PLOT", "MEDIUM"),
        (7, "聊斋志异中哪个故事最著名？", "PLOT", "EASY"),
        (8, "搜神记主要记载了什么内容？", "PLOT", "MEDIUM"),
        (9, "山海经中记载了哪些神兽？", "ENTITY", "EASY"),
        (10, "武松的性格特点是什么？", "CHARACTER", "EASY"),
        (10, "林冲被逼上梁山的原因是什么？", "PLOT", "MEDIUM"),
        (10, "宋江为什么能当上梁山首领？", "CHARACTER", "HARD"),
    ]
    for book_id, question, category, difficulty in cases:
        c.execute(
            "INSERT INTO novel_eval_case (book_id, question, category, difficulty) VALUES (%s, %s, %s, %s)",
            (book_id, question, category, difficulty)
        )
    conn.commit()
    print(f"Created {len(cases)} cases")
conn.close()

# Run eval
print("\nRunning eval...")
r = httpx.post(
    "http://127.0.0.1:18081/api/eval/run",
    params={"use_deepseek": True},
    timeout=600
)
result = r.json()
print(f"Eval result: {json.dumps(result, ensure_ascii=False, indent=2)}")
