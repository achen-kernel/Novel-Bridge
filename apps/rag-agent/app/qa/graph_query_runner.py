"""
图查询扩展器。
为 QA 阶段提供实体为中心的图扩展上下文。
"""
import logging
from typing import List, Dict, Any, Optional

from app.clients.neo4j_client import neo4j_client
from app.stores.entity_profile_store import EntityProfileStore
from app.stores.event_fact_store import EventFactStore
from app.stores.relation_fact_store import RelationFactStore

logger = logging.getLogger(__name__)


class GraphQueryRunner:
    """图查询扩展器"""

    def __init__(self, conn):
        self.conn = conn
        self.profile_store = EntityProfileStore(conn)
        self.rel_fact_store = RelationFactStore(conn)
        self.ev_fact_store = EventFactStore(conn)

    def expand_context(self, question: str, book_id: int,
                       mentioned_entities: List[str] = None) -> List[Dict[str, Any]]:
        """为 QA 扩展图上下文

        1. 从问题中提取实体名
        2. 从 Neo4j 查询关联实体/事件/关系
        3. 返回上下文片段
        """
        if not mentioned_entities:
            return []

        extra_contexts = []

        for entity_name in mentioned_entities:
            # 1. 从 Neo4j 查询关联
            graph = neo4j_client.get_entity_relations(entity_name, book_id)
            if not graph or not graph.get('entity'):
                continue

            # 2. 提取关联实体
            for rel in graph.get('relations', []):
                target = rel.get('target_entity', {})
                target_name = target.get('name', '')
                rel_type = rel.get('type', '')
                if target_name:
                    extra_contexts.append({
                        'source': 'graph_expansion',
                        'type': 'relation',
                        'text': f"{entity_name} → [{rel_type}] → {target_name}",
                        'relevance': 'medium',
                    })

            # 3. 提取关联事件
            for evt in graph.get('events', []):
                summary = evt.get('summary', '')
                if summary:
                    extra_contexts.append({
                        'source': 'graph_expansion',
                        'type': 'event',
                        'text': f"[事件] {summary}",
                        'relevance': 'medium',
                    })

        # 4. 从 MySQL 补充关系事实详情
        for entity_name in mentioned_entities:
            facts = self.rel_fact_store.find_by_entity(book_id, entity_name)
            for f in facts:
                extra_contexts.append({
                    'source': 'graph_expansion',
                    'type': 'relation_fact',
                    'text': (f"{f['source_entity_name']} → [{f['relation_type']}] "
                             f"→ {f['target_entity_name']} (置信度:{f.get('confidence', 0.0):.2f})"),
                    'relevance': 'medium',
                })

        return extra_contexts
