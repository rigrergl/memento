"""Tests for Memory dataclass (T008-T010)."""
from datetime import datetime, timezone

import pytest

from src.models.memory import Memory


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


def test_memory_creation():
    """T008: Verify Memory with all 10 fields."""
    now = datetime.now(timezone.utc)
    memory = Memory(
        id="550e8400-e29b-41d4-a716-446655440000",
        content="My favorite color is blue",
        embedding=[0.1] * 384,
        confidence=0.85,
        created_at=now,
        updated_at=now,
        accessed_at=now,
        source="user_requested",
        supersedes=None,
        superseded_by=None,
    )
    assert memory.id == "550e8400-e29b-41d4-a716-446655440000"
    assert memory.content == "My favorite color is blue"
    assert memory.confidence == 0.85
    assert memory.source == "user_requested"
    assert memory.supersedes is None
    assert memory.superseded_by is None
    assert memory.created_at == now
    assert memory.updated_at == now
    assert memory.accessed_at == now


def test_memory_field_types():
    """T009: Verify field types — id str, content str, embedding list[float], confidence float, source str, supersedes/superseded_by Optional[str], timestamps datetime."""
    memory = _make_memory()
    assert isinstance(memory.id, str)
    assert isinstance(memory.content, str)
    assert isinstance(memory.embedding, list)
    assert all(isinstance(v, float) for v in memory.embedding)
    assert isinstance(memory.confidence, float)
    assert isinstance(memory.source, str)
    assert memory.supersedes is None or isinstance(memory.supersedes, str)
    assert memory.superseded_by is None or isinstance(memory.superseded_by, str)
    assert isinstance(memory.created_at, datetime)
    assert isinstance(memory.updated_at, datetime)
    assert isinstance(memory.accessed_at, datetime)


def test_memory_embedding_dimensions():
    """T010: Verify embedding has exactly 384 dimensions."""
    memory = _make_memory()
    assert len(memory.embedding) == 384


def test_memory_source_default():
    """Verify source defaults to 'user_requested' when not provided."""
    memory = _make_memory()
    assert memory.source == "user_requested"
