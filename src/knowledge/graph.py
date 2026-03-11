import logging
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.config import settings

logger = logging.getLogger(__name__)

class KnowledgeGraph:
    """
    Persistent Knowledge Substrate Integration using Neo4j.
    Maintains semantic networks for each brand's marketing domain, audience relationships, and playbook.
    """
    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self._driver = None

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def connect(self):
        """Establish connection to Neo4j with automatic retries."""
        try:
            self._driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
            await self._driver.verify_connectivity()
            logger.info("Connected to Knowledge Graph (Neo4j)")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j (retrying): {e}")
            raise

    async def close(self):
        """Close connection to Neo4j."""
        if self._driver:
            await self._driver.close()

    async def create_node(self, label: str, properties: Dict[str, Any]) -> str:
        """Create a generic entity node."""
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        query = f"CREATE (n:{label} {{{props_str}}}) RETURN id(n) AS node_id"

        async def work(tx):
            result = await tx.run(query, **properties)
            record = await result.single()
            return record["node_id"]

        async with self._driver.session() as session:
            return await session.execute_write(work)

    async def create_relationship(self, node1_id: int, node2_id: int, relationship_type: str, properties: Dict[str, Any] = None) -> int:
        """Create a relationship between two nodes."""
        props = properties or {}
        props_str = ", ".join([f"{k}: ${k}" for k in props.keys()])
        props_clause = f" {{{props_str}}}" if props_str else ""

        query = (
            f"MATCH (a), (b) WHERE id(a) = $node1_id AND id(b) = $node2_id "
            f"CREATE (a)-[r:{relationship_type}{props_clause}]->(b) RETURN id(r) AS rel_id"
        )

        params = {"node1_id": node1_id, "node2_id": node2_id, **props}

        async def work(tx):
            result = await tx.run(query, **params)
            record = await result.single()
            return record["rel_id"]

        async with self._driver.session() as session:
            return await session.execute_write(work)

    async def get_node_by_property(self, label: str, key: str, value: Any) -> Optional[Dict[str, Any]]:
        """Retrieve a node by a specific property."""
        query = f"MATCH (n:{label} {{{key}: $value}}) RETURN n, id(n) as node_id"

        async def work(tx):
            result = await tx.run(query, value=value)
            record = await result.single()
            if record:
                node_dict = dict(record["n"].items())
                node_dict["_id"] = record["node_id"]
                return node_dict
            return None

        async with self._driver.session() as session:
            return await session.execute_read(work)

    async def query(self, cypher_query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a raw Cypher query (for complex agent reasoning)."""
        params = parameters or {}

        async def work(tx):
            result = await tx.run(cypher_query, **params)
            records = await result.data()
            return records

        async with self._driver.session() as session:
            return await session.execute_read(work)

    # Specific Ontology Methods
    async def add_strategy_lineage(self, parent_strategy_id: str, child_strategy_id: str, mutation_type: str):
        """Link two strategies to represent evolutionary history."""
        # Ensure both nodes exist (represented as Strategy instances)
        parent_node = await self.get_node_by_property("Strategy", "strategy_id", parent_strategy_id)
        child_node = await self.get_node_by_property("Strategy", "strategy_id", child_strategy_id)

        if not parent_node or not child_node:
            logger.warning("Could not link lineage: One or both strategy nodes missing.")
            return

        query = (
            "MATCH (p:Strategy {strategy_id: $parent_id}), (c:Strategy {strategy_id: $child_id}) "
            "MERGE (p)-[r:MUTATES_TO {type: $mutation_type, timestamp: timestamp()}]->(c) "
            "RETURN id(r)"
        )

        async def work(tx):
            await tx.run(query, parent_id=parent_strategy_id, child_id=child_strategy_id, mutation_type=mutation_type)

        async with self._driver.session() as session:
            await session.execute_write(work)
