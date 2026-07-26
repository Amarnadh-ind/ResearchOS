"""
Layer 3: Knowledge Graph (Neo4j)
Graph-based knowledge storage for claims, concepts, and relationships.
"""

import structlog
from neo4j import AsyncDriver, AsyncGraphDatabase

from config.settings import get_settings

logger = structlog.get_logger()


class KnowledgeGraph:
    """Neo4j-backed knowledge graph for research relationships.
    Falls back to in-memory storage when Neo4j is unavailable."""

    def __init__(self):
        settings = get_settings()
        self._driver: AsyncDriver | None = None
        self._uri = settings.neo4j_uri
        self._user = settings.neo4j_user
        self._password = settings.neo4j_password
        self._using_fallback = False
        self._in_memory_claims: list[dict] = []
        self._in_memory_concepts: list[dict] = []

    async def connect(self):
        if self._driver is None and not self._using_fallback:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    self._uri, auth=(self._user, self._password)
                )
                # Verify connectivity
                async with self._driver.session() as session:
                    await session.run("RETURN 1")
                logger.info("neo4j_connected")
            except Exception as e:
                logger.warning("neo4j_unavailable_using_memory", error=str(e))
                self._using_fallback = True

    async def disconnect(self):
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def add_claim(
        self,
        session_id: str,
        claim_id: str,
        claim_text: str,
        source_url: str,
        confidence: float,
    ):
        """Add a claim node with source relationship."""
        if self._using_fallback:
            self._in_memory_claims.append(
                {
                    "id": claim_id,
                    "session_id": session_id,
                    "text": claim_text,
                    "source_url": source_url,
                    "confidence": confidence,
                }
            )
            return
        await self.connect()
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (s:Session {id: $session_id})
                MERGE (src:Source {url: $source_url})
                CREATE (c:Claim {
                    id: $claim_id,
                    text: $claim_text,
                    confidence: $confidence
                })
                CREATE (c)-[:BELONGS_TO]->(s)
                CREATE (c)-[:SOURCED_FROM]->(src)
                """,
                session_id=session_id,
                claim_id=claim_id,
                claim_text=claim_text,
                source_url=source_url,
                confidence=confidence,
            )

    async def add_concept_relation(
        self,
        concept_a: str,
        concept_b: str,
        relation: str,
        session_id: str,
    ):
        """Add or merge a relationship between concepts."""
        if self._using_fallback:
            self._in_memory_concepts.append(
                {
                    "source": concept_a,
                    "target": concept_b,
                    "type": relation,
                    "session": session_id,
                }
            )
            return
        await self.connect()
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (a:Concept {name: $concept_a})
                MERGE (b:Concept {name: $concept_b})
                MERGE (a)-[r:RELATED_TO {type: $relation, session: $session_id}]->(b)
                """,
                concept_a=concept_a,
                concept_b=concept_b,
                relation=relation,
                session_id=session_id,
            )

    async def get_claims_for_session(self, session_id: str) -> list[dict]:
        """Retrieve all claims for a session with their sources."""
        if self._using_fallback:
            return [c for c in self._in_memory_claims if c.get("session_id") == session_id]
        await self.connect()
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Claim)-[:BELONGS_TO]->(s:Session {id: $session_id})
                OPTIONAL MATCH (c)-[:SOURCED_FROM]->(src:Source)
                RETURN c.id as id, c.text as text, c.confidence as confidence,
                       src.url as source_url
                """,
                session_id=session_id,
            )
            records = [record.data() async for record in result]
            return records

    async def get_concept_graph(self, session_id: str) -> dict:
        """Get the concept graph for a session."""
        if self._using_fallback:
            edges = [c for c in self._in_memory_concepts if c.get("session") == session_id]
            nodes = set()
            for e in edges:
                nodes.add(e["source"])
                nodes.add(e["target"])
            return {"nodes": list(nodes), "edges": edges}
        await self.connect()
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Concept)-[r:RELATED_TO {session: $session_id}]->(b:Concept)
                RETURN a.name as source, b.name as target, r.type as relation
                """,
                session_id=session_id,
            )
            edges = [record.data() async for record in result]
            nodes = set()
            for e in edges:
                nodes.add(e["source"])
                nodes.add(e["target"])
            return {"nodes": list(nodes), "edges": edges}

    async def clear(self):
        """Clear all nodes and relationships in the Neo4j database."""
        if self._using_fallback:
            self._in_memory_claims.clear()
            self._in_memory_concepts.clear()
            logger.info("in_memory_graph_cleared")
            return
        await self.connect()
        try:
            async with self._driver.session() as session:
                await session.run("MATCH (n) DETACH DELETE n")
            logger.info("neo4j_graph_cleared")
        except Exception as e:
            logger.error("failed_clearing_neo4j", error=str(e))


_knowledge_graph: KnowledgeGraph | None = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
    return _knowledge_graph
