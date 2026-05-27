"""
Neo4j 图数据库客户端。
"""
import logging
from typing import List, Optional

from app.clients.base import BaseClient

logger = logging.getLogger(__name__)


class Neo4jClient(BaseClient):
    """Neo4j 图数据库操作"""

    def __init__(self):
        self._driver = None
        self._configured = False
        self._config = {}

    def configure(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """配置连接参数（惰性连接）"""
        self._config = {
            "uri": uri,
            "user": user,
            "password": password,
            "database": database,
        }
        self._configured = True

    def _connect(self):
        """惰性建立 Neo4j 连接"""
        if self._driver is not None:
            return
        if not self._configured:
            logger.warning("Neo4j not configured — operations will no-op")
            return
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self._config["uri"],
                auth=(self._config["user"], self._config["password"]),
            )
            logger.info("Connected to Neo4j at %s", self._config["uri"])
        except Exception as e:
            logger.error("Failed to connect to Neo4j: %s", e)
            self._driver = None

    def _run(self, query: str, params: dict = None) -> list:
        """执行查询并返回记录"""
        self._connect()
        if self._driver is None:
            return []
        try:
            with self._driver.session(database=self._config.get("database", "neo4j")) as session:
                result = session.run(query, params or {})
                return [dict(r) for r in result]
        except Exception as e:
            logger.error("Neo4j query error: %s", e)
            return []

    # ---- Entity nodes ---- #

    def create_entity_node(self, entity_id: int, name: str,
                           entity_type: str = "CHARACTER",
                           description: str = "",
                           aliases: list = None,
                           mention_count: int = 0,
                           book_id: int = 0):
        """创建或更新实体节点"""
        if not self._configured:
            return
        self._run(
            """MERGE (e:Entity {entity_id: $entity_id})
               SET e.name = $name,
                   e.entity_type = $entity_type,
                   e.description = $description,
                   e.aliases = $aliases,
                   e.mention_count = $mention_count,
                   e.book_id = $book_id""",
            {
                "entity_id": entity_id,
                "name": name,
                "entity_type": entity_type,
                "description": description,
                "aliases": aliases or [],
                "mention_count": mention_count,
                "book_id": book_id,
            },
        )

    # ---- Relation edges ---- #

    def create_relation_edge(self, source_id: int, target_id: int,
                              relation_type: str, family: str = "OTHER",
                              polarity: str = "NEUTRAL",
                              confidence: float = 0.0,
                              strength: int = 1):
        """创建或更新实体间关系边"""
        if not self._configured:
            return
        self._run(
            """MATCH (s:Entity {entity_id: $source_id})
               MATCH (t:Entity {entity_id: $target_id})
               MERGE (s)-[r:RELATED_TO {type: $relation_type}]->(t)
               SET r.family = $family,
                   r.polarity = $polarity,
                   r.confidence = $confidence,
                   r.strength = $strength""",
            {
                "source_id": source_id,
                "target_id": target_id,
                "relation_type": relation_type,
                "family": family,
                "polarity": polarity,
                "confidence": confidence,
                "strength": strength,
            },
        )

    # ---- Event nodes ---- #

    def create_event_node(self, event_id: int, summary: str,
                           event_type: str = "OTHER",
                           importance: str = "MEDIUM",
                           participants: list = None,
                           book_id: int = 0):
        """创建事件节点"""
        if not self._configured:
            return
        self._run(
            """MERGE (e:Event {event_id: $event_id})
               SET e.summary = $summary,
                   e.event_type = $event_type,
                   e.importance = $importance,
                   e.participants = $participants,
                   e.book_id = $book_id""",
            {
                "event_id": event_id,
                "summary": summary,
                "event_type": event_type,
                "importance": importance,
                "participants": participants or [],
                "book_id": book_id,
            },
        )

    def create_participated_in(self, entity_id: int, event_id: int):
        """创建 PARTICIPATED_IN 关系"""
        if not self._configured:
            return
        self._run(
            """MATCH (e:Entity {entity_id: $entity_id})
               MATCH (ev:Event {event_id: $event_id})
               MERGE (e)-[:PARTICIPATED_IN]->(ev)""",
            {"entity_id": entity_id, "event_id": event_id},
        )

    # ---- Plot stage nodes ---- #

    def create_plot_stage_node(self, stage_id: int, name: str,
                                index: int, summary: str = "",
                                book_id: int = 0):
        """创建故事阶段节点"""
        if not self._configured:
            return
        self._run(
            """MERGE (s:PlotStage {stage_id: $stage_id})
               SET s.name = $name,
                   s.index = $index,
                   s.summary = $summary,
                   s.book_id = $book_id""",
            {"stage_id": stage_id, "name": name, "index": index, "summary": summary, "book_id": book_id},
        )

    # ---- Query ---- #

    def get_entity_relations(self, entity_name: str, book_id: int) -> dict:
        """获取实体的关联实体和事件"""
        if not self._configured:
            return {"entity": None, "relations": [], "events": []}

        entity_records = self._run(
            "MATCH (e:Entity) WHERE e.name = $name RETURN e LIMIT 1",
            {"name": entity_name},
        )
        if not entity_records:
            return {"entity": None, "relations": [], "events": []}

        entity = entity_records[0].get("e")

        # 关联实体
        rel_records = self._run(
            """MATCH (e:Entity {name: $name})-[r:RELATED_TO]->(target:Entity)
               RETURN target, r.type AS type""",
            {"name": entity_name},
        )
        relations = []
        for rec in rel_records:
            relations.append({
                "target_entity": rec.get("target"),
                "type": rec.get("type"),
            })

        # 关联事件
        ev_records = self._run(
            """MATCH (e:Entity {name: $name})-[:PARTICIPATED_IN]->(ev:Event)
               RETURN ev""",
            {"name": entity_name},
        )
        events = [rec.get("ev") for rec in ev_records if rec.get("ev")]

        return {"entity": entity, "relations": relations, "events": events}

    # ---- Clear ---- #

    def clear_book(self, book_id: int):
        """清除指定 book_id 的所有节点和关系（book-scoped 清除）

        使用 book_id 属性精确匹配，避免误删其他书的数据。
        """
        if not self._configured or not book_id:
            return
        self._run("MATCH (n {book_id: $book_id}) DETACH DELETE n", {"book_id": book_id})
        self._run("MATCH (n) WHERE n.book_id = $book_id DETACH DELETE n", {"book_id": book_id})
        logger.info(f"Cleared Neo4j data for book_id={book_id}")

    def clear_all(self):
        """清除所有节点和关系——高阶操作，调用前确认"""
        if not self._configured:
            return
        self._run("MATCH (n) DETACH DELETE n")
        logger.info("Cleared all Neo4j data")

    async def health_check(self) -> dict:
        if not self._configured:
            return {"status": "configured", "detail": "Neo4j client configured (no connection)"}
        self._connect()
        if self._driver is None:
            return {"status": "unavailable", "detail": "Neo4j connection failed"}
        try:
            with self._driver.session(database=self._config.get("database", "neo4j")) as session:
                session.run("RETURN 1")
                return {"status": "ok", "detail": "Neo4j connected"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}


# 模块级单例
neo4j_client = Neo4jClient()
