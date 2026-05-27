"""
图投影器。
将 MySQL 中的实体档案、关系事实、事件事实投影到 Neo4j。
"""
import json
import logging
from typing import Optional

from app.clients.neo4j_client import neo4j_client
from app.stores.entity_profile_store import EntityProfileStore
from app.stores.event_fact_store import EventFactStore
from app.stores.plot_stage_store import PlotStageStore
from app.stores.relation_fact_store import RelationFactStore

logger = logging.getLogger(__name__)


class GraphProjector:
    """投影 MySQL → Neo4j"""

    def __init__(self, conn):
        self.conn = conn
        self.profile_store = EntityProfileStore(conn)
        self.rel_fact_store = RelationFactStore(conn)
        self.ev_fact_store = EventFactStore(conn)
        self.stage_store = PlotStageStore(conn)

    def project_book(self, book_id: int, clear_first: bool = True) -> dict:
        """将一本书的叙事数据投影到 Neo4j

        使用 book-scoped clear（clear_book）而非全局 clear_all，
        避免多书运行时误删其他书的数据。
        """
        if clear_first:
            neo4j_client.clear_book(book_id=book_id)

        # 1. 投影 Entity 节点
        profiles = self.profile_store.find_by_book(book_id)
        entities_by_name = {}
        for prof in profiles:
            aliases = prof.get('aliases_json', '[]')
            if isinstance(aliases, str):
                try:
                    aliases = json.loads(aliases)
                except Exception:
                    aliases = []

            neo4j_client.create_entity_node(
                entity_id=prof['id'],
                name=prof['canonical_name'],
                entity_type=prof.get('entity_type', 'CHARACTER'),
                description=prof.get('description', ''),
                aliases=aliases,
                mention_count=prof.get('mention_count', 0),
                book_id=book_id,
            )
            entities_by_name[prof['canonical_name']] = prof['id']

        logger.info(f"Projected {len(profiles)} entity nodes")

        # 2. 投影 Relation 边
        relations = self.rel_fact_store.find_by_book(book_id)
        edge_count = 0
        for rel in relations:
            source_name = rel['source_entity_name']
            target_name = rel['target_entity_name']
            source_id = entities_by_name.get(source_name)
            target_id = entities_by_name.get(target_name)

            if source_id and target_id:
                neo4j_client.create_relation_edge(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=rel['relation_type'],
                    family=rel.get('relation_family', 'OTHER'),
                    polarity=rel.get('polarity', 'NEUTRAL'),
                    confidence=rel.get('confidence', 0.0),
                    strength=rel.get('strength', 1),
                )
                edge_count += 1

        logger.info(f"Projected {edge_count} relation edges")

        # 3. 投影 Event 节点 + PARTICIPATED_IN 边
        events = self.ev_fact_store.find_by_book(book_id)
        event_count = 0
        for evt in events:
            participants = evt.get('participants_json', '[]')
            if isinstance(participants, str):
                try:
                    participants = json.loads(participants)
                except Exception:
                    participants = []

            neo4j_client.create_event_node(
                event_id=evt['id'],
                summary=evt.get('summary', ''),
                event_type=evt.get('event_type', 'OTHER'),
                importance=evt.get('importance', 'MEDIUM'),
                participants=participants,
                book_id=book_id,
            )

            # 创建参与关系
            for p_name in participants:
                p_id = entities_by_name.get(p_name)
                if p_id:
                    neo4j_client.create_participated_in(p_id, evt['id'])

            event_count += 1

        logger.info(f"Projected {event_count} event nodes")

        # 4. 投影 PlotStage 节点
        stages = self.stage_store.find_by_book(book_id)
        for stage in stages:
            neo4j_client.create_plot_stage_node(
                stage_id=stage['id'],
                name=stage['stage_name'],
                index=stage['stage_index'],
                summary=stage.get('summary', ''),
                book_id=book_id,
            )

        logger.info(f"Projected {len(stages)} plot stage nodes")

        return {
            'entities': len(profiles),
            'relations': edge_count,
            'events': event_count,
            'plot_stages': len(stages),
        }
