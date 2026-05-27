"""
叙事构建器。
从 ChapterFact 和 EntityProfile 提取关系/事件 mention 和 fact。
"""
import json
import logging
from typing import List, Dict, Optional

import pymysql

from app.clients.mysql_client import MysqlClient
from app.stores.event_fact_store import EventFactStore
from app.stores.event_mention_store import EventMentionStore
from app.stores.model_run_store import ModelRunStore
from app.stores.relation_fact_store import RelationFactStore
from app.stores.relation_mention_store import RelationMentionStore

logger = logging.getLogger(__name__)


class NarrativeBuilder:
    """从 ChapterFact 构建叙事元素"""

    def __init__(self, db: MysqlClient):
        self.db = db

    def build_from_book(self, book_id: int, run_id: Optional[int] = None) -> dict:
        """从一本书的 ChapterFacts 构建关系/事件 mentions + facts"""
        conn = self.db.connect()
        run_store = ModelRunStore(conn)
        rel_mention_store = RelationMentionStore(conn)
        rel_fact_store = RelationFactStore(conn)
        ev_mention_store = EventMentionStore(conn)
        ev_fact_store = EventFactStore(conn)

        if run_id is None:
            run_id = run_store.create_run('NARRATIVE_BUILD', book_id, {'book_id': book_id})

        try:
            # 1. 读取所有 ChapterFacts
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, chapter_id, fact_json, evidence_json FROM novel_chapter_fact WHERE book_id = %s",
                    (book_id,)
                )
                facts = cursor.fetchall()

            logger.info(f"Narrative: processing {len(facts)} chapters for book {book_id}")

            all_relations = []
            all_events = []

            for fact in facts:
                fact_json = fact.get('fact_json', {})
                if isinstance(fact_json, str):
                    try:
                        fact_json = json.loads(fact_json)
                    except Exception:
                        fact_json = {}

                chapter_id = fact['chapter_id']

                # 提取关系
                for rel in fact_json.get('relations', []):
                    all_relations.append({
                        'book_id': book_id,
                        'chapter_id': chapter_id,
                        'chunk_id': None,
                        'source_entity_name': rel.get('source', ''),
                        'target_entity_name': rel.get('target', ''),
                        'relation_type': rel.get('relation_type', 'OTHER'),
                        'relation_family': rel.get('relation_family', 'OTHER'),
                        'relation_polarity': 'UNKNOWN',
                        'direction': 'UNKNOWN',
                        'evidence_text': '',
                        'relation_trigger': '',
                        'confidence': rel.get('confidence', 0.0),
                    })

                # 提取事件（description 和 summary 都兼容）
                for evt in fact_json.get('events', []):
                    all_events.append({
                        'book_id': book_id,
                        'chapter_id': chapter_id,
                        'chunk_id': None,
                        'event_type': evt.get('event_type', 'OTHER'),
                        'summary': evt.get('summary') or evt.get('description', ''),
                        'participants': evt.get('participants', []),
                        'location': evt.get('location', ''),
                        'time_hint': evt.get('time_hint', ''),
                        'event_trigger': evt.get('event_trigger', ''),
                        'evidence_text': '',
                        'importance': evt.get('importance', 'MEDIUM'),
                        'confidence': evt.get('confidence', 0.0),
                    })

            # 2. 写入 relation mentions
            step_id = run_store.create_step(run_id, 'BUILD_RELATION_MENTIONS', 1,
                                            {'book_id': book_id, 'count': len(all_relations)})
            rel_mention_count = rel_mention_store.insert_batch(all_relations)
            run_store.update_step_status(step_id, 'SUCCESS', {'inserted': rel_mention_count})

            # 3. 写入 event mentions
            step_id = run_store.create_step(run_id, 'BUILD_EVENT_MENTIONS', 2,
                                            {'book_id': book_id, 'count': len(all_events)})
            ev_mention_count = ev_mention_store.insert_batch(all_events)
            run_store.update_step_status(step_id, 'SUCCESS', {'inserted': ev_mention_count})

            # 4. 聚合 relation facts (去重+计数)
            step_id = run_store.create_step(run_id, 'BUILD_RELATION_FACTS', 3,
                                            {'book_id': book_id})
            fact_count = 0
            for rel in all_relations:
                if rel['source_entity_name'] and rel['target_entity_name']:
                    rel_fact_store.upsert(
                        book_id=book_id,
                        source_name=rel['source_entity_name'],
                        target_name=rel['target_entity_name'],
                        relation_type=rel['relation_type'],
                        relation_family=rel['relation_family'],
                        polarity=rel['relation_polarity'],
                        confidence=rel['confidence'],
                        chapter_id=rel['chapter_id']
                    )
                    fact_count += 1
            run_store.update_step_status(step_id, 'SUCCESS', {'facts': fact_count})

            # 5. 聚合 event facts
            step_id = run_store.create_step(run_id, 'BUILD_EVENT_FACTS', 4,
                                            {'book_id': book_id})
            ev_fact_count = 0
            for evt in all_events:
                if evt['event_type'] and evt['summary']:
                    ev_fact_store.upsert(
                        book_id=book_id,
                        event_type=evt['event_type'],
                        summary=evt['summary'],
                        participants=evt.get('participants', []),
                        location=evt.get('location', ''),
                        importance=evt.get('importance', 'MEDIUM'),
                        chapter_id=evt['chapter_id']
                    )
                    ev_fact_count += 1
            run_store.update_step_status(step_id, 'SUCCESS', {'facts': ev_fact_count})

            run_store.update_run_status(run_id, 'SUCCESS', {
                'book_id': book_id,
                'relation_mentions': rel_mention_count,
                'event_mentions': ev_mention_count,
                'relation_facts': fact_count,
                'event_facts': ev_fact_count,
            })

            return {
                'status': 'success', 'book_id': book_id,
                'relation_mentions': rel_mention_count,
                'event_mentions': ev_mention_count,
                'relation_facts': fact_count,
                'event_facts': ev_fact_count,
                'run_id': run_id,
            }

        except Exception as e:
            logger.error(f"Narrative build failed: {e}")
            run_store.update_run_status(run_id, 'FAILED', error_type=type(e).__name__, error_message=str(e))
            return {'status': 'error', 'book_id': book_id, 'error': str(e)}
