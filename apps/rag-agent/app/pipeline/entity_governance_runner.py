"""
实体治理编排器。
对一本书的所有 entity mentions 执行:
1. 泛称检测
2. 别名安全决策
3. 实体档案构建
4. 章节视图生成
"""
import json
import logging
from typing import List, Optional

from app.clients.mysql_client import MysqlClient
from app.stores.alias_decision_store import AliasDecisionStore
from app.stores.entity_mention_store import EntityMentionStore
from app.stores.entity_profile_store import EntityProfileStore
from app.stores.model_run_store import ModelRunStore
from app.validators.alias_validator import (
    is_generic_mention,
    should_block_merge,
    get_chapter_entity_view,
)

logger = logging.getLogger(__name__)


class EntityGovernanceRunner:
    """实体治理编排器"""

    def __init__(self, db: MysqlClient):
        self.db = db

    def process_book(self, book_id: int, run_id: Optional[int] = None) -> dict:
        """对一本书执行实体治理"""
        conn = self.db.connect()
        run_store = ModelRunStore(conn)
        mention_store = EntityMentionStore(conn)
        profile_store = EntityProfileStore(conn)
        decision_store = AliasDecisionStore(conn)

        # 读取 prior_hint 中的 alias_risks，用于辅助别名决策
        alias_risks = {}
        with conn.cursor() as cursor:
            cursor.execute("SELECT prior_hint_json FROM novel_book WHERE id = %s", (book_id,))
            row = cursor.fetchone()
            if row and row.get('prior_hint_json'):
                try:
                    ph = json.loads(row['prior_hint_json']) if isinstance(row['prior_hint_json'], str) else row['prior_hint_json']
                    for risk_item in ph.get('alias_risks', []):
                        if isinstance(risk_item, dict):
                            name = risk_item.get('name', '')
                            if name:
                                aliases = risk_item.get('aliases', [])
                                alias_risks[name] = {'aliases': aliases, 'risk': risk_item.get('risk', '')}
                except Exception:
                    pass

        if run_id is None:
            run_id = run_store.create_run('ENTITY_GOVERNANCE', book_id, {'book_id': book_id})

        try:
            # 1. 读取已有的 ChapterFacts，提取所有实体
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, chapter_id, fact_json FROM novel_chapter_fact WHERE book_id = %s",
                    (book_id,)
                )
                facts = cursor.fetchall()

            logger.info(f"Governance: processing {len(facts)} chapters for book {book_id}")

            all_mentions = []
            entity_descriptions = {}  # canonical_name -> list of description snippets

            for fact in facts:
                fact_json = fact.get('fact_json', {})
                if isinstance(fact_json, str):
                    try:
                        fact_json = json.loads(fact_json)
                    except Exception:
                        fact_json = {}

                chars = fact_json.get('characters', [])
                for char in chars:
                    display_name = char.get('display_name', '')
                    # 收集 description
                    desc = char.get('description', '') or ''
                    if desc and display_name:
                        if display_name not in entity_descriptions:
                            entity_descriptions[display_name] = []
                        entity_descriptions[display_name].append(desc)

                    surface_texts = char.get('surface_texts', [display_name])
                    for st in surface_texts:
                        generic = is_generic_mention(st)
                        mention = {
                            'book_id': book_id,
                            'chapter_id': fact['chapter_id'],
                            'chunk_id': None,
                            'surface_text': st,
                            'normalized_name': display_name or st,
                            'entity_type': 'CHARACTER',
                            'mention_role': 'GENERIC_MENTION' if generic else 'CANONICAL',
                            'confidence': char.get('confidence', 0.3),
                            'is_generic': generic,
                            'do_not_merge_globally': generic or char.get('alias_risk', False),
                            'evidence_text': '',
                        }
                        all_mentions.append(mention)

            # 2. 批量写入 entity_mention
            step_id = run_store.create_step(run_id, 'BUILD_MENTIONS', 1,
                                            {'book_id': book_id, 'mention_count': len(all_mentions)})
            mention_store.insert_mentions_batch(all_mentions)
            run_store.update_step_status(step_id, 'SUCCESS', {'inserted': len(all_mentions)})

            # 3. 批量决策别名
            step_id = run_store.create_step(run_id, 'ALIAS_REVIEW', 2,
                                            {'book_id': book_id, 'mention_count': len(all_mentions)})

            decisions = self._make_alias_decisions(all_mentions, decision_store, book_id, alias_risks)
            run_store.update_step_status(step_id, 'SUCCESS', {
                'decisions': len(decisions),
                'merges': sum(1 for d in decisions if d['decision'] == 'MERGE'),
                'blocks': sum(1 for d in decisions if d['decision'] == 'BLOCK'),
            })

            # 4. 构建 Entity Profiles（传入收集的描述）
            step_id = run_store.create_step(run_id, 'BUILD_PROFILES', 3,
                                            {'book_id': book_id})

            # 合并描述：同一实体的多个 snippets 拼接为一段
            merged_descriptions = {}
            for name, descs in entity_descriptions.items():
                # 去重 + 拼接
                unique = list(dict.fromkeys(d.strip() for d in descs if d.strip()))
                if unique:
                    merged_descriptions[name] = '；'.join(unique[:5])

            profiles = self._build_profiles(all_mentions, decisions, merged_descriptions)
            for prof in profiles:
                profile_store.insert_profile(
                    book_id=book_id,
                    canonical_name=prof['canonical_name'],
                    entity_type=prof.get('entity_type', 'CHARACTER'),
                    description=prof.get('description', ''),
                    aliases=prof.get('aliases', []),
                    first_chapter_id=prof.get('first_chapter_id'),
                    last_chapter_id=prof.get('last_chapter_id'),
                    mention_count=prof.get('mention_count', 0),
                    source='GOVERNED'
                )

            run_store.update_step_status(step_id, 'SUCCESS', {'profiles': len(profiles)})

            run_store.update_run_status(run_id, 'SUCCESS', {
                'book_id': book_id,
                'total_mentions': len(all_mentions),
                'total_profiles': len(profiles),
                'decisions': len(decisions),
            })

            return {
                'status': 'success',
                'book_id': book_id,
                'mentions': len(all_mentions),
                'profiles': len(profiles),
                'decisions': len(decisions),
                'run_id': run_id,
            }

        except Exception as e:
            logger.error(f"Entity governance failed for book {book_id}: {e}")
            run_store.update_run_status(run_id, 'FAILED', error_type=type(e).__name__, error_message=str(e))
            return {'status': 'error', 'book_id': book_id, 'error': str(e)}

    def _make_alias_decisions(self, mentions: List[dict],
                               decision_store: AliasDecisionStore,
                               book_id: int,
                               alias_risks: dict = None) -> List[dict]:
        """对同一 chapter 内的所有实体做两两对比

        如果 prior_hint 提供了 alias_risks，会在规则决策的基础上
        添加别名合并提示（MERGE 偏好）。
        """
        if alias_risks is None:
            alias_risks = {}

        # 构建别名查找表: name -> set of known aliases from prior_hint
        prior_alias_map = {}
        for canon, info in alias_risks.items():
            prior_alias_map[canon] = set(info.get('aliases', []))
            for alias in info.get('aliases', []):
                if alias not in prior_alias_map:
                    prior_alias_map[alias] = set()
                prior_alias_map[alias].add(canon)

        decisions = []

        # 按章节分组
        chapter_groups = {}
        for m in mentions:
            ch = m['chapter_id']
            name = m.get('normalized_name', m['surface_text'])
            if ch not in chapter_groups:
                chapter_groups[ch] = set()
            chapter_groups[ch].add(name)

        for ch, names in chapter_groups.items():
            name_list = list(names)
            for i in range(len(name_list)):
                for j in range(i + 1, len(name_list)):
                    a, b = name_list[i], name_list[j]
                    decision, reason, confidence = should_block_merge(a, b)

                    # 检查 prior_hint 的别名风险提示
                    # 如果 DeepSeek 说 a 是 b 的别名（或反之），倾向 MERGE
                    if decision != 'MERGE':
                        if a in prior_alias_map and b in prior_alias_map[a]:
                            decision = 'MERGE'
                            reason += '; prior_hint 提示为别名'
                            confidence = max(confidence, 0.7)
                        elif b in prior_alias_map and a in prior_alias_map[b]:
                            decision = 'MERGE'
                            reason += '; prior_hint 提示为别名'
                            confidence = max(confidence, 0.7)

                    decisions.append({
                        'book_id': book_id,
                        'entity_a_name': a,
                        'entity_b_name': b,
                        'decision': decision,
                        'confidence': confidence,
                        'reason': reason,
                        'risk_types': [],
                        'reviewer': 'RULE',
                    })

                    decision_store.insert_decision(
                        book_id=book_id,
                        entity_a_name=a,
                        entity_b_name=b,
                        decision=decision,
                        confidence=confidence,
                        reason=reason,
                        risk_types=[],
                        reviewer='RULE',
                    )

        return decisions

    def _build_profiles(self, mentions: List[dict],
                        decisions: List[dict],
                        descriptions: dict = None) -> List[dict]:
        """构建实体档案（已经决策后）

        Args:
            mentions: entity mentions 列表
            decisions: 别名决策列表
            descriptions: {canonical_name: description} 映射（从 extraction 收集）
        """
        if descriptions is None:
            descriptions = {}
        # 合并规则: 从 decisions 中找出所有 MERGE 决策
        merge_map = {}  # name -> set of aliases
        for d in decisions:
            if d['decision'] == 'MERGE':
                canon = d['entity_a_name']
                alias = d['entity_b_name']
                if canon not in merge_map:
                    merge_map[canon] = set()
                merge_map[canon].add(alias)
                if alias not in merge_map:
                    merge_map[alias] = set()
                merge_map[alias].add(canon)

        processed = set()
        profiles = []

        for m in mentions:
            name = m.get('normalized_name', m['surface_text'])
            if name in processed:
                continue

            # 找到这个实体的所有别名
            alias_set = {name}
            if name in merge_map:
                alias_set.update(merge_map[name])

            processed.add(name)
            for a in alias_set:
                processed.add(a)

            # 收集这个实体的所有 mentions
            entity_mentions = [x for x in mentions
                               if x.get('normalized_name', x['surface_text']) in alias_set]

            if not entity_mentions:
                continue

            chapter_ids = [m['chapter_id'] for m in entity_mentions if m.get('chapter_id')]
            entity_type = entity_mentions[0].get('entity_type', 'CHARACTER')

            # 从收集的描述中查找
            profile_desc = ''
            for n in alias_set:
                if n in descriptions and descriptions[n]:
                    profile_desc = descriptions[n]
                    break

            profiles.append({
                'canonical_name': name,
                'entity_type': entity_type,
                'description': profile_desc,
                'aliases': list(alias_set - {name}),
                'first_chapter_id': min(chapter_ids) if chapter_ids else None,
                'last_chapter_id': max(chapter_ids) if chapter_ids else None,
                'mention_count': len(entity_mentions),
            })

        return profiles
