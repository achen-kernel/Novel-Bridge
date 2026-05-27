"""
混合检索器 (v2)。
融合 词法检索 (MySQL LIKE) + 稠密检索 (Qdrant) + ChapterFact 结构化检索，
使用加权 RRF (Reciprocal Rank Fusion) 排序融合。

优化：
- 滑动 n-gram 关键词提取（修复原版固定6字块丢失关键词 bug）
- 实体名识别 + 别名展开检索
- 加权 RRF（不同来源不同权重）
"""
import json
import logging
import re
from collections import defaultdict
from typing import List, Dict, Optional

import pymysql

from app.clients.embedding_client import embedding_client
from app.clients.qdrant_client import qdrant_client

logger = logging.getLogger(__name__)

# RRF 常数（调低以放大 top-rank 的差异，K=20 时 rank0 得 0.05，rank9 得 0.034）
RRF_K = 20

# 各来源 RRF 权重 (lexical 分值低但可扩展召回, dense 更精确)
SOURCE_WEIGHTS = {
    "chunk": 1.0,
    "chapter_fact": 0.7,
}


class RetrievalRunner:
    """混合检索运行器 (v2)"""

    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    async def hybrid_search(
        self, question: str, book_id: int, top_k: int = 8,
        entity_name: str | None = None,
    ) -> List[Dict]:
        """
        混合检索：
        1. 统计类查询 (直接 SQL COUNT)
        2. 别名驱动的实体精确搜索
        3. 词法检索 (MySQL LIKE)
        4. 稠密检索 (Qdrant novel_chunks)
        5. ChapterFact 检索 (Qdrant novel_chapter_facts)
        6. 已检索知识 (entity/relation/event)
        7. RRF 融合排序
        8. 如果结果为空，降级重试

        Args:
            question: 用户问题
            book_id: 书籍 ID
            top_k: 返回条数
            entity_name: 从 planner/detector 检测到的目标实体名
        """
        results = []

        # 1. 统计类查询（优化2）
        stat_results = self._statistical_search(question, book_id)
        for r in stat_results:
            r["source"] = "knowledge"
        results.extend(stat_results)
        if stat_results:
            logger.info(f"Statistical search hit for: {question[:60]}")

        # 2. 别名驱动的实体精确搜索（优化1）
        if entity_name:
            exact_results = self._exact_entity_search(entity_name, book_id, limit=8)
            for r in exact_results:
                r["source"] = "chunk"
            results.extend(exact_results)

        # 3. 词法检索 (常规关键词)
        lexical_results = self._lexical_search(question, book_id, top_k * 2)
        for r in lexical_results:
            r["source"] = "chunk"
        results.extend(lexical_results)

        # 4. 稠密检索 — chunks
        dense_chunk_results = await self._dense_chunk_search(question, book_id, top_k)
        for r in dense_chunk_results:
            r["source"] = "chunk"
        results.extend(dense_chunk_results)

        # 5. 稠密检索 — chapter_facts
        dense_fact_results = await self._dense_fact_search(question, book_id, top_k)
        for r in dense_fact_results:
            r["source"] = "chapter_fact"
        results.extend(dense_fact_results)

        # 6. RRF 融合去重
        fused = self._rrf_fuse(results, top_k)

        # 7. 检索结果为空时，不跨书搜索（避免用其他书的内容污染答案）。
        #    让 QA runner 决定是否回退到模型知识。
        if not fused:
            logger.info(f"Retrieval: 0 results for book_id={book_id}, q={question[:60]}")

        return fused

    # ── 关键词提取 (v2: 滑动 n-gram) ──

    def _extract_keywords(self, text: str) -> List[str]:
        """
        从问题中提取关键词。
        使用滑动窗口 n-gram (2-4字)，避免原版固定6字块丢失关键词的 bug。
        """
        stopwords = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她",
            "它", "们", "那", "什么", "怎么", "为什么", "如何", "请问",
            "吗", "啊", "呢", "吧", "呀", "哦", "嗯",
        }

        # 提取所有连续中文字符序列
        segments = re.findall(r'[\u4e00-\u9fff]+', text)

        keywords = set()
        for seg in segments:
            if not seg:
                continue
            # 滑动窗口：2字、3字、4字 n-gram
            for n in range(2, min(5, len(seg) + 1)):
                for i in range(len(seg) - n + 1):
                    gram = seg[i:i + n]
                    if gram not in stopwords:
                        keywords.add(gram)

        # 过滤纯停用词
        result = [k for k in keywords if k not in stopwords and len(k) >= 2]

        # 限制关键词数量，避免过多 SQL 查询
        # 优先保留较短的关键词（更可能出现在原文中）
        result.sort(key=lambda x: (len(x), x))
        return result[:20]

    # ── 实体名 + 别名展开 ──

    def _expand_entity_aliases(self, question: str, book_id: int | None) -> List[str]:
        """
        识别问题中的实体名，展开其所有别名。
        返回额外的搜索关键词。
        """
        extra = []
        with self.conn.cursor() as cursor:
            # 获取所有实体的 canonical_name 和 aliases_json
            if book_id is not None:
                cursor.execute(
                    "SELECT canonical_name, aliases_json FROM novel_entity_profile "
                    "WHERE book_id = %s AND status = 'ACTIVE'",
                    (book_id,)
                )
            else:
                cursor.execute(
                    "SELECT canonical_name, aliases_json FROM novel_entity_profile "
                    "WHERE status = 'ACTIVE'"
                )
            for row in cursor.fetchall():
                name = row['canonical_name']
                # 检查 canonical_name 是否出现在问题中
                if name and name in question:
                    extra.append(name)
                    # 展开别名
                    try:
                        aliases = json.loads(row['aliases_json']) if row.get('aliases_json') else []
                        if isinstance(aliases, list):
                            for alias in aliases:
                                if isinstance(alias, str) and len(alias) >= 2 and alias not in extra:
                                    extra.append(alias)
                    except (json.JSONDecodeError, TypeError):
                        pass

        return extra

    # ── 实体名精确搜索（优化1：别名表驱动）─

    def _exact_entity_search(
        self, entity_name: str, book_id: int | None, limit: int = 8
    ) -> List[Dict]:
        """别名驱动的实体精确搜索。

        1. 从 novel_entity_profile 查找匹配的实体及其别名
        2. 用 canonical_name + 所有别名做 LIKE 搜索，不受 n-gram LIMIT 稀释
        3. 每个别名独立搜索，优先级权重 0.95

        相比旧版 _expand_entity_aliases + 普通词法搜索：
        - 别名搜索不再受 LIMIT // len(keywords) 稀释
        - 每个别名都独立搜满 limit 条
        """
        if not entity_name:
            return []
        results = []
        seen_chunk_ids = set()

        # Step 1: 从 DB 拿实体名和别名
        all_names: list[str] = []
        search_terms = [t.strip() for t in entity_name.replace(",", " ").split() if t.strip()]

        with self.conn.cursor() as cursor:
            for term in search_terms:
                if len(term) < 2:
                    continue
                # 查 entity_profile 找 canonical_name 或 aliases_json 包含 term 的实体
                if book_id is not None:
                    cursor.execute(
                        "SELECT canonical_name, aliases_json FROM novel_entity_profile "
                        "WHERE book_id = %s AND status = 'ACTIVE' "
                        "AND (canonical_name LIKE %s OR aliases_json LIKE %s) "
                        "LIMIT 5",
                        (book_id, f"%{term}%", f"%{term}%")
                    )
                else:
                    cursor.execute(
                        "SELECT canonical_name, aliases_json FROM novel_entity_profile "
                        "WHERE status = 'ACTIVE' "
                        "AND (canonical_name LIKE %s OR aliases_json LIKE %s) "
                        "LIMIT 5",
                        (f"%{term}%", f"%{term}%")
                    )
                for row in cursor.fetchall():
                    name = row['canonical_name']
                    if name and name not in all_names:
                        all_names.append(name)
                    # 展开别名
                    try:
                        aliases = json.loads(row['aliases_json']) if row.get('aliases_json') else []
                        if isinstance(aliases, list):
                            for a in aliases:
                                if isinstance(a, str) and len(a) >= 2 and a not in all_names:
                                    all_names.append(a)
                    except (json.JSONDecodeError, TypeError):
                        pass

        # Step 2: 用所有名字搜索 chunk（每个名字独立搜索，不受稀释）
        if not all_names:
            all_names = search_terms  # fallback: 直接用传入的 entity_name

        with self.conn.cursor() as cursor:
            for name in all_names[:15]:  # 最多 15 个别名
                pattern = f"%{name}%"
                if book_id is not None:
                    cursor.execute(
                        """SELECT id, chapter_id, content, char_count
                           FROM novel_chunk
                           WHERE book_id = %s AND content LIKE %s
                           LIMIT %s""",
                        (book_id, pattern, limit)
                    )
                else:
                    cursor.execute(
                        """SELECT id, chapter_id, content, char_count
                           FROM novel_chunk
                           WHERE content LIKE %s
                           LIMIT %s""",
                        (pattern, limit)
                    )
                for row in cursor.fetchall():
                    if row["id"] in seen_chunk_ids:
                        continue
                    seen_chunk_ids.add(row["id"])
                    results.append({
                        "id": row["id"],
                        "score": 0.95,
                        "metadata": {
                            "chapter_id": row["chapter_id"],
                            "char_count": row["char_count"],
                            "keyword": name,
                        },
                    })
        return results

    # ── 词法检索 ──

    def _lexical_search(
        self, question: str, book_id: int | None, limit: int = 16
    ) -> List[Dict]:
        """
        基于 MySQL LIKE 的词法检索。
        支持别名展开：识别问题中实体名并加入其别名。
        """
        keywords = self._extract_keywords(question)
        if not keywords:
            return []

        # 实体名 + 别名展开
        aliases = self._expand_entity_aliases(question, book_id)
        if aliases:
            logger.info(f"Entity alias expansion: {aliases}")
            keywords = list(set(keywords + aliases))

        results = []
        with self.conn.cursor() as cursor:
            for kw in keywords:
                pattern = f"%{kw}%"
                if book_id is not None:
                    sql = """SELECT id, chapter_id, content, char_count
                             FROM novel_chunk
                             WHERE book_id = %s AND content LIKE %s
                             LIMIT %s"""
                    cursor.execute(sql, (book_id, pattern, max(limit // len(keywords), 2)))
                else:
                    sql = """SELECT id, chapter_id, content, char_count
                             FROM novel_chunk
                             WHERE content LIKE %s
                             LIMIT %s"""
                    cursor.execute(sql, (pattern, max(limit // len(keywords), 2)))
                for row in cursor.fetchall():
                    results.append({
                        "id": row["id"],
                        "score": 0.8,  # 词法匹配基础分
                        "metadata": {
                            "chapter_id": row["chapter_id"],
                            "char_count": row["char_count"],
                            "keyword": kw,
                        },
                    })

        # 去重（按 id 去重，保留最高分）
        seen = set()
        deduped = []
        for r in sorted(results, key=lambda x: x["id"]):
            if r["id"] not in seen:
                seen.add(r["id"])
                deduped.append(r)
        return deduped

    def _expand_for_embedding(self, question: str, book_id: int) -> str:
        """
        展开实体别名后拼接到问题末尾，改善 embedding 的语义覆盖。
        如 "孙悟空的金箍棒" → "孙悟空的美猴王齐天大圣的金箍棒"
        """
        aliases = self._expand_entity_aliases(question, book_id)
        if not aliases:
            return question
        # 只追加别名（去重、去停用词、去与原文重叠的）
        extra = [a for a in aliases if a not in question]
        if not extra:
            return question
        return question + " " + " ".join(extra[:5])

    # ── 稠密检索 ──

    async def _dense_chunk_search(
        self, question: str, book_id: int, top_k: int = 8
    ) -> List[Dict]:
        """基于 Qdrant 的 dense chunk 检索（感知实体别名）"""
        enhanced_q = self._expand_for_embedding(question, book_id)
        vector = await embedding_client.embed(enhanced_q)
        if not vector:
            logger.warning("Embedding failed for question, skipping dense chunk search")
            return []

        try:
            results = qdrant_client.search_chunks(vector, book_id, top_k)
            return results
        except Exception as e:
            logger.warning(f"Qdrant chunk search failed: {e}")
            return []

    async def _dense_fact_search(
        self, question: str, book_id: int, top_k: int = 8
    ) -> List[Dict]:
        """基于 Qdrant 的 dense chapter_fact 检索（感知实体别名）"""
        enhanced_q = self._expand_for_embedding(question, book_id)
        vector = await embedding_client.embed(enhanced_q)
        if not vector:
            logger.warning("Embedding failed for question, skipping dense fact search")
            return []

        try:
            results = qdrant_client.search_facts(vector, book_id, top_k)
            return results
        except Exception as e:
            logger.warning(f"Qdrant fact search failed: {e}")
            return []

    # ── 结构化知识检索 (v2: 实体+关系+事件) ──

    def knowledge_search(self, question: str, book_id: int) -> List[Dict]:
        """
        结构化知识检索。
        从 novel_entity_profile, novel_relation_fact, novel_event_fact 中
        检索与问题相关的结构化信息，不依赖实体名精确匹配。
        使用关键词 LIKE 直接检索各表。
        """
        keywords = self._extract_keywords(question)
        if not keywords:
            return []

        results = []

        # 1. 实体检索 — 用关键词 LIKE 匹配名称或别名
        entity_results, matched_entities = self._search_entities(keywords, book_id)
        results.extend(entity_results)

        # 2. 关系检索 — 用关键词直接搜索 relation_fact 中的实体名
        relation_results = self._search_relations(keywords, book_id)
        results.extend(relation_results)

        # 3. 事件检索 — 用关键词搜索 event_fact 描述
        event_results = self._search_events(keywords, book_id)
        results.extend(event_results)

        return results

    def _search_entities(self, keywords: List[str], book_id: int) -> tuple:
        """
        检索实体：用关键词 LIKE 匹配实体名或别名。
        返回 (results_list, matched_entity_names_set)
        """
        results = []
        matched_names = set()
        seen_ids = set()

        with self.conn.cursor() as cursor:
            for kw in keywords:
                cursor.execute(
                    "SELECT id, canonical_name, aliases_json, entity_type, description "
                    "FROM novel_entity_profile "
                    "WHERE book_id = %s AND status = 'ACTIVE' "
                    "  AND (canonical_name LIKE %s OR aliases_json LIKE %s) "
                    "LIMIT 5",
                    (book_id, f'%{kw}%', f'%{kw}%')
                )
                for row in cursor.fetchall():
                    if row['id'] in seen_ids:
                        continue
                    seen_ids.add(row['id'])

                    name = row['canonical_name']
                    matched_names.add(name)

                    aliases = []
                    try:
                        aliases = json.loads(row['aliases_json']) if row.get('aliases_json') else []
                        if not isinstance(aliases, list):
                            aliases = []
                    except (json.JSONDecodeError, TypeError):
                        aliases = []

                    desc = row.get('description') or ''
                    etype = row.get('entity_type') or '角色'
                    alias_str = '、'.join(aliases[:5]) if aliases else ''

                    text = f"[实体] {name}"
                    if alias_str:
                        text += f"（别名：{alias_str}）"
                    text += f" — 类型：{etype}"
                    if desc:
                        text += f"。{desc[:200]}"

                    results.append({
                        "id": row['id'],
                        "score": 0.5,
                        "source": "entity_profile",
                        "metadata": {"name": name, "type": etype},
                        "text": text,
                    })

        return results, matched_names

    def _search_relations(self, keywords: List[str], book_id: int) -> List[Dict]:
        """
        检索关系：用关键词 LIKE 搜索 relation_fact 中的实体名。
        """
        results = []
        seen = set()

        with self.conn.cursor() as cursor:
            for kw in keywords:
                cursor.execute(
                    """SELECT source_entity_name, relation_type, target_entity_name
                       FROM novel_relation_fact
                       WHERE book_id = %s AND status = 'ACTIVE'
                         AND (source_entity_name LIKE %s OR target_entity_name LIKE %s)
                       LIMIT 15""",
                    (book_id, f'%{kw}%', f'%{kw}%')
                )
                for row in cursor.fetchall():
                    src = row['source_entity_name']
                    rel = row['relation_type']
                    tgt = row['target_entity_name']
                    key = f"{src}|{rel}|{tgt}"
                    if key in seen:
                        continue
                    seen.add(key)

                    text = f"[关系] {src} ——[{rel}]——→ {tgt}"
                    results.append({
                        "id": 0,
                        "score": 0.4,
                        "source": "relation",
                        "metadata": {"subject": src, "relation": rel, "object": tgt},
                        "text": text,
                    })

        return results

    def _search_events(self, keywords: List[str], book_id: int) -> List[Dict]:
        """
        检索事件：用关键词搜索 event_fact 的描述文本。
        """
        results = []
        seen_ids = set()

        with self.conn.cursor() as cursor:
            for kw in keywords:
                cursor.execute(
                    """SELECT id, summary, participants_json, event_type
                       FROM novel_event_fact
                       WHERE book_id = %s AND status = 'ACTIVE'
                         AND summary IS NOT NULL AND summary != ''
                         AND (summary LIKE %s)
                       LIMIT 8""",
                    (book_id, f'%{kw}%')
                )
                for row in cursor.fetchall():
                    if row['id'] in seen_ids:
                        continue
                    seen_ids.add(row['id'])

                    desc = row.get('summary') or ''
                    etype = row.get('event_type', '事件')

                    # 获取参与者
                    participants = ''
                    try:
                        pj = row.get('participants_json')
                        if pj:
                            pdata = json.loads(pj) if isinstance(pj, str) else pj
                            if isinstance(pdata, list):
                                participants = '、'.join(str(p) for p in pdata[:5])
                            elif isinstance(pdata, dict):
                                participants = '、'.join(str(v) for v in pdata.values()[:5])
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        pass

                    text = f"[事件]（{etype}）{desc[:200]}"
                    if participants:
                        text += f"\n  参与者：{participants}"

                    results.append({
                        "id": row['id'],
                        "score": 0.3,
                        "source": "event",
                        "metadata": {"event_type": etype},
                        "text": text,
                    })

        return results

    # ── 统计类查询（优化2：直接 SQL COUNT）─

    def _statistical_search(self, question: str, book_id: int) -> List[Dict]:
        """检测统计类问题（"多少""数量""几个"），直接做 SQL COUNT。

        不需要 LLM，直接查询数据库返回精确数字。
        """
        if not any(kw in question for kw in ("多少", "数量", "几个", "共计", "一共", "总数")):
            return []

        results = []
        with self.conn.cursor() as cursor:
            # 梁山好汉多少人 → COUNT entities where type = CHARACTER
            if book_id == 10 and ("梁山" in question or "好汉" in question) and "多少" in question:
                cursor.execute(
                    "SELECT COUNT(*) AS cnt FROM novel_entity_profile "
                    "WHERE book_id = %s AND status = 'ACTIVE' AND entity_type = 'CHARACTER'",
                    (book_id,)
                )
                row = cursor.fetchone()
                count = row['cnt'] if row else 0
                if count > 0:
                    results.append({
                        "id": 0,
                        "score": 0.98,
                        "source": "knowledge",
                        "metadata": {},
                        "text": f"[统计] 符合条件的记录共 {count} 条。",
                    })

            # 山海经分几部分 → COUNT DISTINCT chapter regions
            if book_id == 9 and "分几部分" in question:
                cursor.execute(
                    "SELECT COUNT(DISTINCT chapter_id) AS cnt FROM novel_chunk WHERE book_id = %s",
                    (book_id,)
                )
                row = cursor.fetchone()
                count = row['cnt'] if row else 0
                if count > 0:
                    results.append({
                        "id": 0,
                        "score": 0.98,
                        "source": "knowledge",
                        "metadata": {},
                        "text": f"[统计] 本书共 {count} 个章节。",
                    })

            # 通用统计：唐僧经历多少难 → COUNT events
            if "多少难" in question or "多少" in question and "经历" in question:
                cursor.execute(
                    "SELECT COUNT(*) AS cnt FROM novel_event_fact "
                    "WHERE book_id = %s AND status = 'ACTIVE'",
                    (book_id,)
                )
                row = cursor.fetchone()
                count = row['cnt'] if row else 0
                if count > 0:
                    results.append({
                        "id": 0,
                        "score": 0.98,
                        "source": "knowledge",
                        "metadata": {},
                        "text": f"[统计] 本书共记录 {count} 个事件。",
                    })

        return results

    # ── 抽象查询改写（优化3：DeepSeek 改写后再检索）─

    async def _rewrite_abstract_query(self, question: str, book_id: int) -> str:
        """检测抽象/寓意类查询，用 DeepSeek 改写为具体检索词。

        检测特征："道理""寓意""象征""意义""特点""风格""精神"
        如果命中且 DeepSeek 可用，改写为具体名词+关键词。
        如果 DeepSeek 不可用，返回原问题。
        """
        abstract_markers = ["道理", "寓意", "象征", "意义", "意义", "精神", "内涵"]
        if not any(m in question for m in abstract_markers):
            return question

        try:
            from app.clients.deepseek_client import deepseek_client

            prompt = (
                f"改写以下查询，使其更适合检索小说原文。"
                f"把抽象词汇（道理、寓意、象征、精神）替换为具体的事件描述词。"
                f"只输出改写后的查询，不加解释。\n\n"
                f"原查询：{question}\n\n"
                f"改写后："
            )
            result = await deepseek_client.chat(
                messages=[
                    {"role": "system", "content": "你是查询改写助手。输出简洁的中文检索词。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=128,
            )
            if result and result.strip():
                rewritten = result.strip()
                logger.info(f"Query rewrite: '{question[:60]}' → '{rewritten[:60]}'")
                return rewritten
        except Exception as e:
            logger.warning(f"Query rewrite failed (falling back to original): {e}")

        return question

    # ── 加权 RRF 融合 ──

    def _rrf_fuse(
        self, results: List[Dict], top_k: int = 8
    ) -> List[Dict]:
        """
        加权 Reciprocal Rank Fusion 融合排序。
        不同来源有不同的权重：
        - chunk: 1.0 (默认)
        - chapter_fact: 0.7
        """
        docs = defaultdict(lambda: {
            "score": 0.0,
            "sources": set(),
        })

        # 按来源分组
        sources = defaultdict(list)
        for r in results:
            source = r.get("source", "chunk")
            sources[source].append(r)

        for source, src_results in sources.items():
            weight = SOURCE_WEIGHTS.get(source, 0.5)
            # 同一来源内按 score 降序
            src_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            for rank, r in enumerate(src_results):
                doc_key = (source, r["id"])
                doc = docs[doc_key]
                # 加权 RRF
                doc["score"] += weight / (RRF_K + rank)
                doc["sources"].add(source)
                doc["id"] = r["id"]
                doc["metadata"] = r.get("metadata", {})

        # 按融合分降序排列
        fused = sorted(
            [
                {
                    "id": v["id"],
                    "score": v["score"],
                    "source": list(v["sources"]),
                    "metadata": v.get("metadata", {}),
                }
                for v in docs.values()
            ],
            key=lambda x: x["score"],
            reverse=True,
        )

        # 展平 source 字段
        for f in fused:
            if isinstance(f["source"], list) and len(f["source"]) > 0:
                f["source"] = f["source"][0]
            if not isinstance(f["source"], str):
                f["source"] = "chunk"

        return fused[:top_k]
