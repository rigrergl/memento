"""Tests for Neo4jRepository (T011-T017, T064-T066)."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.models.memory import Memory


def _make_memory(**kwargs) -> Memory:
    defaults = dict(
        id="550e8400-e29b-41d4-a716-446655440000",
        content="My favorite color is blue",
        embedding=[0.1] * 384,
        confidence=0.85,
        created_at=datetime(2025, 12, 24, 10, 30, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 12, 24, 10, 30, 0, tzinfo=timezone.utc),
        accessed_at=datetime(2025, 12, 24, 10, 30, 0, tzinfo=timezone.utc),
    )
    defaults.update(kwargs)
    return Memory(**defaults)


# ---------------------------------------------------------------------------
# T011: Neo4jRepository initialization
# ---------------------------------------------------------------------------

def test_neo4j_repository_init():
    """T011: Verify Neo4jRepository initializes with driver using URI, user, password."""
    with patch("src.graph.neo4j.GraphDatabase") as mock_gdb:
        mock_driver = MagicMock()
        mock_gdb.driver.return_value = mock_driver

        from src.graph.neo4j import Neo4jRepository
        repo = Neo4jRepository(uri="bolt://localhost:7687", user="neo4j", password="secret")

        mock_gdb.driver.assert_called_once_with(
            "bolt://localhost:7687", auth=("neo4j", "secret")
        )
        assert repo._driver is mock_driver


# ---------------------------------------------------------------------------
# T012: create_memory success
# ---------------------------------------------------------------------------

def test_create_memory_success():
    """T012: Mock session.run, verify correct Cypher query and parameters."""
    with patch("src.graph.neo4j.GraphDatabase") as mock_gdb:
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        from src.graph.neo4j import Neo4jRepository
        repo = Neo4jRepository(uri="bolt://localhost:7687", user="neo4j", password="secret")
        memory = _make_memory()
        repo.create_memory(memory)

        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        cypher = call_args[0][0]
        assert "CREATE" in cypher
        assert ":Memory" in cypher


# ---------------------------------------------------------------------------
# T013: ensure_vector_index creates index and constraint
# ---------------------------------------------------------------------------

def test_ensure_vector_index_creates_index():
    """T013: Mock session.run, verify vector index Cypher (384 dims, cosine) and uniqueness constraint."""
    with patch("src.graph.neo4j.GraphDatabase") as mock_gdb:
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        from src.graph.neo4j import Neo4jRepository
        repo = Neo4jRepository(uri="bolt://localhost:7687", user="neo4j", password="secret")
        repo.ensure_vector_index()

        assert mock_session.run.call_count == 2
        calls = [call[0][0] for call in mock_session.run.call_args_list]
        combined = " ".join(calls)
        assert "384" in combined
        assert "cosine" in combined
        assert "CONSTRAINT" in combined


# ---------------------------------------------------------------------------
# T014: ensure_vector_index is idempotent (IF NOT EXISTS)
# ---------------------------------------------------------------------------

def test_ensure_vector_index_idempotent():
    """T014: Mock session.run, verify IF NOT EXISTS pattern in both statements."""
    with patch("src.graph.neo4j.GraphDatabase") as mock_gdb:
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        from src.graph.neo4j import Neo4jRepository
        repo = Neo4jRepository(uri="bolt://localhost:7687", user="neo4j", password="secret")
        repo.ensure_vector_index()

        calls = [call[0][0] for call in mock_session.run.call_args_list]
        combined = " ".join(calls)
        assert combined.count("IF NOT EXISTS") == 2


# ---------------------------------------------------------------------------
# T015: create_memory with all 10 fields
# ---------------------------------------------------------------------------

def test_create_memory_with_all_fields():
    """T015: Mock session.run, verify all 10 Memory fields appear in Cypher parameters."""
    with patch("src.graph.neo4j.GraphDatabase") as mock_gdb:
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        from src.graph.neo4j import Neo4jRepository
        repo = Neo4jRepository(uri="bolt://localhost:7687", user="neo4j", password="secret")
        memory = _make_memory()
        repo.create_memory(memory)

        call_kwargs = mock_session.run.call_args[1]
        for field in ("id", "content", "embedding", "confidence", "created_at",
                      "updated_at", "accessed_at", "source", "supersedes", "superseded_by"):
            assert field in call_kwargs, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# T016: repository close
# ---------------------------------------------------------------------------

def test_repository_close():
    """T016: Mock driver, verify driver.close() is called on Neo4jRepository.close()."""
    with patch("src.graph.neo4j.GraphDatabase") as mock_gdb:
        mock_driver = MagicMock()
        mock_gdb.driver.return_value = mock_driver

        from src.graph.neo4j import Neo4jRepository
        repo = Neo4jRepository(uri="bolt://localhost:7687", user="neo4j", password="secret")
        repo.close()

        mock_driver.close.assert_called_once()


# ---------------------------------------------------------------------------
# T017: create_memory propagates Neo4j failure
# ---------------------------------------------------------------------------

def test_create_memory_neo4j_failure():
    """T017: Mock session.run to raise ServiceUnavailable, verify exception propagates."""
    from neo4j.exceptions import ServiceUnavailable

    with patch("src.graph.neo4j.GraphDatabase") as mock_gdb:
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.side_effect = ServiceUnavailable("Neo4j down")
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        from src.graph.neo4j import Neo4jRepository
        repo = Neo4jRepository(uri="bolt://localhost:7687", user="neo4j", password="secret")
        memory = _make_memory()

        with pytest.raises(ServiceUnavailable):
            repo.create_memory(memory)


# ---------------------------------------------------------------------------
# T064: search_memories returns results
# ---------------------------------------------------------------------------

def test_search_memories_returns_results():
    """T064: Mock session.run returning records, verify correct vector search Cypher and (Memory, float) tuples."""
    with patch("src.graph.neo4j.GraphDatabase") as mock_gdb:
        mock_driver = MagicMock()
        mock_session = MagicMock()

        memory = _make_memory()
        mock_record = MagicMock()
        mock_node = {
            "id": memory.id,
            "content": memory.content,
            "embedding": memory.embedding,
            "confidence": memory.confidence,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at,
            "accessed_at": memory.accessed_at,
            "source": memory.source,
            "supersedes": memory.supersedes,
            "superseded_by": memory.superseded_by,
        }
        mock_record.__getitem__ = lambda self, key: mock_node if key == "m" else 0.95
        mock_session.run.return_value = [mock_record]

        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        from src.graph.neo4j import Neo4jRepository
        repo = Neo4jRepository(uri="bolt://localhost:7687", user="neo4j", password="secret")
        results = repo.search_memories(embedding=[0.1] * 384, limit=5)

        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        cypher = call_args[0][0]
        assert "queryNodes" in cypher or "vector" in cypher.lower()
        assert len(results) == 1
        assert isinstance(results[0], tuple)
        assert isinstance(results[0][0], Memory)
        assert isinstance(results[0][1], float)


# ---------------------------------------------------------------------------
# T065: search_memories empty results
# ---------------------------------------------------------------------------

def test_search_memories_empty_results():
    """T065: Mock session.run returning empty list, verify empty list returned."""
    with patch("src.graph.neo4j.GraphDatabase") as mock_gdb:
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.return_value = []
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        from src.graph.neo4j import Neo4jRepository
        repo = Neo4jRepository(uri="bolt://localhost:7687", user="neo4j", password="secret")
        results = repo.search_memories(embedding=[0.1] * 384, limit=10)

        assert results == []


# ---------------------------------------------------------------------------
# T066: search_memories preserves order from Neo4j response
# ---------------------------------------------------------------------------

def test_search_memories_returns_ordered_results():
    """T066: Mock session returning multiple records, verify results list preserves Neo4j order."""
    with patch("src.graph.neo4j.GraphDatabase") as mock_gdb:
        mock_driver = MagicMock()
        mock_session = MagicMock()

        def make_record(content: str, score: float):
            memory = _make_memory(content=content)
            node = {
                "id": memory.id,
                "content": memory.content,
                "embedding": memory.embedding,
                "confidence": memory.confidence,
                "created_at": memory.created_at,
                "updated_at": memory.updated_at,
                "accessed_at": memory.accessed_at,
                "source": memory.source,
                "supersedes": memory.supersedes,
                "superseded_by": memory.superseded_by,
            }
            record = MagicMock()
            record.__getitem__ = lambda self, key: node if key == "m" else score
            return record

        records = [make_record("first", 0.95), make_record("second", 0.80)]
        mock_session.run.return_value = records
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        from src.graph.neo4j import Neo4jRepository
        repo = Neo4jRepository(uri="bolt://localhost:7687", user="neo4j", password="secret")
        results = repo.search_memories(embedding=[0.1] * 384, limit=10)

        assert len(results) == 2
        assert results[0][0].content == "first"
        assert results[1][0].content == "second"
