"""Neo4j implementation of IGraphRepository."""
from neo4j import GraphDatabase

from src.graph.base import IGraphRepository
from src.models.memory import Memory


class Neo4jRepository(IGraphRepository):
    """Repository for Memory nodes in Neo4j."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def ensure_vector_index(self) -> None:
        """Create vector index (384 dims, cosine) and uniqueness constraint if not present."""
        with self._driver.session() as session:
            session.run(
                "CREATE VECTOR INDEX memory_embedding_index IF NOT EXISTS "
                "FOR (m:Memory) ON m.embedding "
                "OPTIONS { indexConfig: { `vector.dimensions`: 384, `vector.similarity_function`: 'cosine' } }"
            )
            session.run(
                "CREATE CONSTRAINT memory_id_unique IF NOT EXISTS "
                "FOR (m:Memory) REQUIRE m.id IS UNIQUE"
            )

    def create_memory(self, memory: Memory) -> None:
        """Persist a Memory node with all 10 fields."""
        with self._driver.session() as session:
            session.run(
                "CREATE (:Memory { "
                "id: $id, content: $content, embedding: $embedding, "
                "confidence: $confidence, created_at: $created_at, "
                "updated_at: $updated_at, accessed_at: $accessed_at, "
                "source: $source, supersedes: $supersedes, superseded_by: $superseded_by "
                "})",
                id=memory.id,
                content=memory.content,
                embedding=memory.embedding,
                confidence=memory.confidence,
                created_at=memory.created_at,
                updated_at=memory.updated_at,
                accessed_at=memory.accessed_at,
                source=memory.source,
                supersedes=memory.supersedes,
                superseded_by=memory.superseded_by,
            )

    def search_memories(self, embedding: list[float], limit: int) -> list[tuple[Memory, float]]:
        """Vector similarity search; returns (Memory, score) pairs in Neo4j order."""
        with self._driver.session() as session:
            records = session.run(
                "CALL db.index.vector.queryNodes('memory_embedding_index', $limit, $embedding) "
                "YIELD node AS m, score RETURN m, score",
                limit=limit,
                embedding=embedding,
            )
            results = []
            for record in records:
                node = record["m"]
                score = record["score"]
                memory = Memory(
                    id=node["id"],
                    content=node["content"],
                    embedding=list(node["embedding"]),
                    confidence=node["confidence"],
                    created_at=node["created_at"],
                    updated_at=node["updated_at"],
                    accessed_at=node["accessed_at"],
                    source=node["source"],
                    supersedes=node["supersedes"],
                    superseded_by=node["superseded_by"],
                )
                results.append((memory, float(score)))
            return results

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        self._driver.close()
