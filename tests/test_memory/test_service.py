"""Tests for MemoryService (T018-T026, T067-T072, T089)."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.models.memory import Memory


def _make_config(**kwargs):
    cfg = MagicMock()
    cfg.max_memory_length = kwargs.get("max_memory_length", 4000)
    return cfg


def _make_memory(**kwargs) -> Memory:
    defaults = dict(
        id="550e8400-e29b-41d4-a716-446655440000",
        content="My favorite color is blue",
        embedding=[0.1] * 384,
        confidence=0.85,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        accessed_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Memory(**defaults)


# ---------------------------------------------------------------------------
# T018: MemoryService initialization
# ---------------------------------------------------------------------------

def test_memory_service_init():
    """T018: Verify MemoryService initializes with config, embedder, repository."""
    from src.memory.service import MemoryService

    config = _make_config()
    embedder = MagicMock()
    repository = MagicMock()

    service = MemoryService(config=config, embedder=embedder, repository=repository)
    assert service._config is config
    assert service._embedder is embedder
    assert service._repository is repository


# ---------------------------------------------------------------------------
# T019: store_memory success
# ---------------------------------------------------------------------------

def test_store_memory_success():
    """T019: Mock embedder and repository, verify successful memory storage with UUID generation."""
    from src.memory.service import MemoryService

    config = _make_config()
    embedder = MagicMock()
    embedder.generate_embedding.return_value = [0.1] * 384
    repository = MagicMock()

    service = MemoryService(config=config, embedder=embedder, repository=repository)
    memory = service.store_memory("My favorite color is blue", 0.85)

    assert isinstance(memory, Memory)
    assert memory.content == "My favorite color is blue"
    assert memory.confidence == 0.85
    assert len(memory.id) > 0
    repository.create_memory.assert_called_once_with(memory)


# ---------------------------------------------------------------------------
# T020: store_memory empty content rejected
# ---------------------------------------------------------------------------

def test_store_memory_empty_text_rejected():
    """T020: Verify ValueError for empty content."""
    from src.memory.service import MemoryService

    service = MemoryService(config=_make_config(), embedder=MagicMock(), repository=MagicMock())

    with pytest.raises(ValueError):
        service.store_memory("", 0.5)


# ---------------------------------------------------------------------------
# T021: store_memory whitespace-only content rejected
# ---------------------------------------------------------------------------

def test_store_memory_whitespace_rejected():
    """T021: Verify ValueError for whitespace-only content."""
    from src.memory.service import MemoryService

    service = MemoryService(config=_make_config(), embedder=MagicMock(), repository=MagicMock())

    with pytest.raises(ValueError):
        service.store_memory("   \n\t  ", 0.5)


# ---------------------------------------------------------------------------
# T022: store_memory exceeds max_length
# ---------------------------------------------------------------------------

def test_store_memory_exceeds_max_length():
    """T022: Verify ValueError for content exceeding max_memory_length."""
    from src.memory.service import MemoryService

    config = _make_config(max_memory_length=10)
    service = MemoryService(config=config, embedder=MagicMock(), repository=MagicMock())

    with pytest.raises(ValueError):
        service.store_memory("x" * 11, 0.5)


# ---------------------------------------------------------------------------
# T023: store_memory invalid confidence
# ---------------------------------------------------------------------------

def test_store_memory_confidence_validation():
    """T023: Verify ValueError for confidence < 0.0 or > 1.0."""
    from src.memory.service import MemoryService

    service = MemoryService(config=_make_config(), embedder=MagicMock(), repository=MagicMock())

    with pytest.raises(ValueError):
        service.store_memory("valid content", -0.1)

    with pytest.raises(ValueError):
        service.store_memory("valid content", 1.5)


# ---------------------------------------------------------------------------
# T024: store_memory generates embedding
# ---------------------------------------------------------------------------

def test_store_memory_generates_embedding():
    """T024: Mock embedder, verify generate_embedding called with correct content."""
    from src.memory.service import MemoryService

    embedder = MagicMock()
    embedder.generate_embedding.return_value = [0.1] * 384
    service = MemoryService(config=_make_config(), embedder=embedder, repository=MagicMock())

    service.store_memory("My favorite color is blue", 0.85)

    embedder.generate_embedding.assert_called_once_with("My favorite color is blue")


# ---------------------------------------------------------------------------
# T025: store_memory sets timestamps
# ---------------------------------------------------------------------------

def test_store_memory_sets_timestamps():
    """T025: Verify created_at, updated_at, accessed_at all set to same value."""
    from src.memory.service import MemoryService

    embedder = MagicMock()
    embedder.generate_embedding.return_value = [0.1] * 384
    service = MemoryService(config=_make_config(), embedder=embedder, repository=MagicMock())

    memory = service.store_memory("My favorite color is blue", 0.85)

    assert memory.created_at == memory.updated_at == memory.accessed_at


# ---------------------------------------------------------------------------
# T026: store_memory embedding failure propagates
# ---------------------------------------------------------------------------

def test_store_memory_embedding_failure():
    """T026: Mock embedder to raise RuntimeError, verify exception propagates from service."""
    from src.memory.service import MemoryService

    embedder = MagicMock()
    embedder.generate_embedding.side_effect = RuntimeError("model crashed")
    service = MemoryService(config=_make_config(), embedder=embedder, repository=MagicMock())

    with pytest.raises(RuntimeError):
        service.store_memory("valid content", 0.5)


# ---------------------------------------------------------------------------
# T067: search_memory success
# ---------------------------------------------------------------------------

def test_search_memory_success():
    """T067: Mock embedder and repository, verify service returns list[tuple[Memory, float]]."""
    from src.memory.service import MemoryService

    memory = _make_memory()
    embedder = MagicMock()
    embedder.generate_embedding.return_value = [0.1] * 384
    repository = MagicMock()
    repository.search_memories.return_value = [(memory, 0.9)]

    service = MemoryService(config=_make_config(), embedder=embedder, repository=repository)
    results = service.search_memory("color preferences", 10)

    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], tuple)
    assert isinstance(results[0][0], Memory)
    assert isinstance(results[0][1], float)


# ---------------------------------------------------------------------------
# T068: search_memory empty query rejected
# ---------------------------------------------------------------------------

def test_search_memory_empty_query_rejected():
    """T068: Verify ValueError for empty query string."""
    from src.memory.service import MemoryService

    service = MemoryService(config=_make_config(), embedder=MagicMock(), repository=MagicMock())

    with pytest.raises(ValueError):
        service.search_memory("", 10)


# ---------------------------------------------------------------------------
# T069: search_memory whitespace-only query rejected
# ---------------------------------------------------------------------------

def test_search_memory_whitespace_rejected():
    """T069: Verify ValueError for whitespace-only query."""
    from src.memory.service import MemoryService

    service = MemoryService(config=_make_config(), embedder=MagicMock(), repository=MagicMock())

    with pytest.raises(ValueError):
        service.search_memory("   \t\n  ", 10)


# ---------------------------------------------------------------------------
# T070: search_memory generates embedding from query
# ---------------------------------------------------------------------------

def test_search_memory_generates_embedding():
    """T070: Mock embedder, verify generate_embedding called with the query text."""
    from src.memory.service import MemoryService

    embedder = MagicMock()
    embedder.generate_embedding.return_value = [0.1] * 384
    repository = MagicMock()
    repository.search_memories.return_value = []

    service = MemoryService(config=_make_config(), embedder=embedder, repository=repository)
    service.search_memory("color preferences", 10)

    embedder.generate_embedding.assert_called_once_with("color preferences")


# ---------------------------------------------------------------------------
# T071: search_memory embedding failure propagates
# ---------------------------------------------------------------------------

def test_search_memory_embedding_failure():
    """T071: Mock embedder to raise RuntimeError, verify exception propagates from service."""
    from src.memory.service import MemoryService

    embedder = MagicMock()
    embedder.generate_embedding.side_effect = RuntimeError("model crashed")
    service = MemoryService(config=_make_config(), embedder=embedder, repository=MagicMock())

    with pytest.raises(RuntimeError):
        service.search_memory("valid query", 10)


# ---------------------------------------------------------------------------
# T072: search_memory no results
# ---------------------------------------------------------------------------

def test_search_memory_no_results():
    """T072: Mock repository returning empty list, verify empty list returned from service."""
    from src.memory.service import MemoryService

    embedder = MagicMock()
    embedder.generate_embedding.return_value = [0.1] * 384
    repository = MagicMock()
    repository.search_memories.return_value = []

    service = MemoryService(config=_make_config(), embedder=embedder, repository=repository)
    results = service.search_memory("color preferences", 10)

    assert results == []


# ---------------------------------------------------------------------------
# T089: search_memory invalid limit
# ---------------------------------------------------------------------------

def test_search_memory_invalid_limit():
    """T089: Verify ValueError('Limit must be at least 1.') raised when limit < 1."""
    from src.memory.service import MemoryService

    service = MemoryService(config=_make_config(), embedder=MagicMock(), repository=MagicMock())

    with pytest.raises(ValueError, match="Limit must be at least 1."):
        service.search_memory("valid query", 0)

    with pytest.raises(ValueError, match="Limit must be at least 1."):
        service.search_memory("valid query", -5)
