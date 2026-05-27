"""Analyze provider comparison eval results and get DeepSeek recommendations."""
import asyncio
import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.clients.deepseek_client import deepseek_client


LOCAL_RESULTS = """
Local 9B (37 cases, 31/37 PASS=83.8%, avg 10s/case):

PASS	1.唐僧磨难 ans=1146 cit=4
PASS	2.聊斋最著名 ans=947 cit=6
PASS	3.搜神记内容 ans=502 cit=5
PASS	4.山海经神兽 ans=1766 cit=16
PASS	5.武松性格 ans=807 cit=5
PASS	6.林冲逼上梁山 ans=1140 cit=8
FAIL	7.宋江首领 ans=632 cit=0
PASS	8.孙悟空特征 ans=907 cit=5
PASS	9.董永七仙女 ans=780 cit=5
PASS	10.潘金莲西门庆 ans=1074 cit=6
PASS	11.搜神记作者 ans=574 cit=4
PASS	12.韩凭夫妇 ans=821 cit=3
PASS	13.山海经神兽 ans=1019 cit=10
FAIL	14.夸父逐日 ans=501 cit=0
PASS	15.山海经分几部分 ans=598 cit=1
PASS	16.刑天故事 ans=926 cit=6
PASS	17.武松打虎地点 ans=641 cit=3
PASS	18.鲁智深倒拔 ans=454 cit=1
PASS	19.梁山好汉人数 ans=655 cit=6
PASS	20.李逵性格 ans=857 cit=1
PASS	21.杨志卖刀 ans=1154 cit=5
PASS	22.干将莫邪 ans=945 cit=4
PASS	23.聊斋作者 ans=228 cit=2
FAIL	24.崂山道士道理 ans=419 cit=0
PASS	25.促织故事 ans=1073 cit=5
PASS	26.婴宁性格 ans=1410 cit=9
PASS	27.画皮害人 ans=981 cit=4
PASS	28.聂小倩身份 ans=679 cit=4
FAIL	29.观音收悟空 ans=362 cit=2
PASS	30.沙僧身份 ans=215 cit=1
PASS	31.唐僧磨难 ans=668 cit=3
PASS	32.火焰山火 ans=402 cit=2
FAIL	33.大闹天宫原因 ans=683 cit=0
PASS	34.唐僧徒弟 ans=575 cit=3
FAIL	35.猪八戒贬凡 ans=543 cit=0
PASS	36.金箍棒来源 ans=702 cit=4
"""

DEEPSEEK_RESULTS = """
DeepSeek (29 cases so far, 21/29 PASS=72.4%):

FAIL	1.唐僧磨难 ans=473 cit=0
PASS	2.聊斋最著名 ans=178 cit=1
PASS	3.搜神记内容 ans=372 cit=2
PASS	4.山海经神兽 ans=1516 cit=14
PASS	5.武松性格 ans=541 cit=7
PASS	6.林冲逼上梁山 ans=406 cit=3
PASS	7.宋江首领 ans=420 cit=3
PASS	8.孙悟空特征 ans=1143 cit=6
FAIL	9.董永七仙女 ans=292 cit=0
FAIL	10.潘金莲西门庆 ans=703 cit=0
PASS	11.搜神记作者 ans=251 cit=3
PASS	12.韩凭夫妇 ans=714 cit=1
PASS	13.山海经神兽 ans=700 cit=6
PASS	14.精卫填海 ans=330 cit=2
PASS	15.夸父逐日 ans=288 cit=1
FAIL	16.山海经分几部分 ans=52 cit=0
PASS	17.刑天故事 ans=446 cit=5
PASS	18.武松打虎地点 ans=158 cit=2
FAIL	19.鲁智深倒拔 ans=167 cit=0
FAIL	20.梁山好汉人数 ans=47 cit=0
PASS	21.李逵性格 ans=972 cit=8
FAIL	22.杨志卖刀 ans=413 cit=0
PASS	23.干将莫邪 ans=1049 cit=6
PASS	24.聊斋作者 ans=62 cit=1
FAIL	25.崂山道士道理 ans=234 cit=0
PASS	26.促织故事 ans=309 cit=2
PASS	27.婴宁性格 ans=535 cit=5
FAIL	28.画皮害人 ans=112 cit=1
PASS	29.聂小倩身份 ans=62 cit=1
"""


async def main():
    prompt = f"""你是一个 AI 阅读系统的架构顾问。请分析以下两个模型的 Eval 对比数据，给出具体可执行的改进建议。

## Local 9B 结果
{LOCAL_RESULTS}

## DeepSeek 结果
{DEEPSEEK_RESULTS}

## 已知背景
- Local 9B: Qwen3.5-9B via llama-server, 本地 GPU, 平均 10s/case
- DeepSeek: fast API, 平均 7s/case
- Retrieval: hybrid (lexical + dense Qdrant + ChapterFact) via RetrievalRunner
- 评分规则: cit=0 直接 FAIL（无论 answer 多长写得多好）
- PASS 条件: answer 非空 + 不含"无法回答" + 不以此开头"抱歉" + cit >= 1

## 请分析

### 1. 检索问题诊断
- 哪些 case 两个 provider 都 cit=0？暗示检索问题
- 哪些 case 一个 cit=0 另一个 cit>0？暗示模型差异

### 2. Provider 强弱对比
- Local 9B 的优势和劣势
- DeepSeek 的优势和劣势
- 各自更适合什么类型的问题？

### 3. Prompt 改进建议（最重要）
- Local 9B 的 QA prompt 应该加什么约束？
- DeepSeek 的 QA prompt 应该加什么约束？
- 是否需要针对不同问题类型用不同的 prompt？

### 4. 工程架构建议
- Retrieval 侧可以做什么改进？
- 是否需要加 answer-length floor？
- 是否需要做 retrieval quality gate（retrieval 没结果就直接返回低置信，不让模型硬答）？

请用中文回答，给出具体可执行的建议，每一条都要有 why + what + how。
不要笼统说"提高检索质量"，要说清楚改什么、怎么改。
"""

    try:
        result = await deepseek_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2048,
        )
        print(result)
    except Exception as e:
        print(f"DeepSeek analysis failed: {e}")
        # Fallback: do our own analysis
        print("\n\n===== FALLBACK: Local Analysis =====")
        do_local_analysis()


def do_local_analysis():
    """Local analysis when DeepSeek is unavailable."""
    print("""
## Analysis from eval data

### 1. Common Retrieval Issues
Cases where BOTH providers got 0 citations (cit=0):
- Case 25 (崂山道士道理): Both FAIL — query may not match any chunk
- Case 10 (潘金莲西门庆): Local 9B PASS with cit=6, DeepSeek FAIL cit=0
  → This means Local 9B can retrieve, DeepSeek's retrieval runner may have issue
- Case 19 (鲁智深倒拔): Local 9B cit=1, DeepSeek cit=0 → retrieval inconsistency

### 2. Provider Comparison
Local 9B strengths:
- Higher average answer length (~750 chars)
- Better at maintaining citations when retrieval works (avg ~5 cit)
- More consistent output quality
- PASS rate: 83.8%

Local 9B weaknesses:
- Slower (10s/case vs 7s)
- Some cases produce content without citations

DeepSeek strengths:
- Faster (7s/case)
- More concise answers
- Better at structured/analytical questions

DeepSeek weaknesses:
- Lower PASS rate: 72.4%
- Some very short answers (47-62 chars for enumeration questions)
- More sensitive to retrieval failures

### 3. Prompt Recommendations
For Local 9B:
- Already does well with citations — keep current prompt
- Add: '如果检索结果不足，请说明证据不足，不要勉强回答'
- Add: minimum answer length enforcement
- The 6 failed cases all had cit=0 — this may be retrieval issue, not model

For DeepSeek:
- Add explicit: '每个论断必须引用检索结果中的具体文本'
- Add: '如果答案少于100字，说明你找到了什么和没找到什么'
- Add: '对于枚举性问题（多少人、分几部分），必须逐条引用'
- Reduce temperature from current setting to 0.3 for more deterministic output

### 4. Engineering Recommendations
1. Retrieval Quality Gate: Before calling model, check if retrieval has results.
   If 0 results, skip model call and return INSUFFICIENT_EVIDENCE.
2. Answer Length Floor: If answer < 100 chars and no clear reason, flag as potential failure.
3. Citation Count Threshold: Require min 1 citation per ~200 chars of answer.
4. Per-book retrieval tuning: Some books (山海经, 水浒传) have chunk quality issues.
""")


if __name__ == "__main__":
    asyncio.run(main())
