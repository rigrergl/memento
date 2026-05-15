"""Tests for MCP server tools: remember and recall."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.models.memory import Memory


def _make_memory(**kwargs) -> Memory:
    defaults = dict(
        id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        content="My favorite color is blue",
        embedding=[0.1] * 384,
        confidence=0.85,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        accessed_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Memory(**defaults)


def _get_tool_fn(tool_name: str):
    """Return the raw function backing a registered FastMCP tool."""
    from src.mcp.server import mcp
    tool = asyncio.run(mcp.get_tool(tool_name))
    return tool.fn


def _ctx(service) -> MagicMock:
    """Build a stub Context whose lifespan_context exposes the given service."""
    ctx = MagicMock()
    ctx.lifespan_context = {"service": service}
    return ctx


# ---------------------------------------------------------------------------
# MCP server registers remember tool
# ---------------------------------------------------------------------------

def test_mcp_server_registers_remember_tool():
    from src.mcp.server import mcp
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "remember" in names


# ---------------------------------------------------------------------------
# remember tool returns plain-text str containing "Memory stored with id:"
# ---------------------------------------------------------------------------

def test_remember_tool_valid_input():
    mock_service = MagicMock()
    mock_service.store_memory.return_value = _make_memory()

    result = _get_tool_fn("remember")(ctx=_ctx(mock_service), content="My favorite color is blue", confidence=0.85)

    assert isinstance(result, str)
    assert "Memory stored with id:" in result


# ---------------------------------------------------------------------------
# remember tool returns memory UUID in response
# ---------------------------------------------------------------------------

def test_remember_tool_returns_memory_id():
    memory = _make_memory(id="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    mock_service = MagicMock()
    mock_service.store_memory.return_value = memory

    result = _get_tool_fn("remember")(ctx=_ctx(mock_service), content="My favorite color is blue", confidence=0.85)

    assert "a1b2c3d4-e5f6-7890-abcd-ef1234567890" in result


# ---------------------------------------------------------------------------
# remember tool return type is str
# ---------------------------------------------------------------------------

def test_remember_tool_returns_str_type():
    mock_service = MagicMock()
    mock_service.store_memory.return_value = _make_memory()

    result = _get_tool_fn("remember")(ctx=_ctx(mock_service), content="valid content", confidence=0.5)

    assert type(result) is str


# ---------------------------------------------------------------------------
# remember tool returns error string for empty memory (ValueError)
# ---------------------------------------------------------------------------

def test_remember_tool_empty_memory_error():
    mock_service = MagicMock()
    mock_service.store_memory.side_effect = ValueError("Memory text cannot be empty.")

    result = _get_tool_fn("remember")(ctx=_ctx(mock_service), content="", confidence=0.5)

    assert isinstance(result, str)
    assert "Memory text cannot be empty." in result


# ---------------------------------------------------------------------------
# remember tool returns error string for exceeds max length (ValueError)
# ---------------------------------------------------------------------------

def test_remember_tool_exceeds_max_length_error():
    mock_service = MagicMock()
    mock_service.store_memory.side_effect = ValueError("Memory text exceeds maximum length of 4000 characters")

    result = _get_tool_fn("remember")(ctx=_ctx(mock_service), content="x" * 5000, confidence=0.5)

    assert isinstance(result, str)
    assert "exceeds" in result.lower() or "length" in result.lower()


# ---------------------------------------------------------------------------
# remember tool returns error string for invalid confidence (ValueError)
# ---------------------------------------------------------------------------

def test_remember_tool_invalid_confidence_error():
    mock_service = MagicMock()
    mock_service.store_memory.side_effect = ValueError("Confidence must be between 0.0 and 1.0")

    result = _get_tool_fn("remember")(ctx=_ctx(mock_service), content="valid content", confidence=1.5)

    assert isinstance(result, str)
    assert "confidence" in result.lower() or "0.0" in result


# ---------------------------------------------------------------------------
# remember tool returns error string for embedding failure (RuntimeError)
# ---------------------------------------------------------------------------

def test_remember_tool_embedding_failure():
    mock_service = MagicMock()
    mock_service.store_memory.side_effect = RuntimeError("model crashed")

    result = _get_tool_fn("remember")(ctx=_ctx(mock_service), content="valid content", confidence=0.5)

    assert isinstance(result, str)
    assert "Failed to store memory" in result


# ---------------------------------------------------------------------------
# remember tool returns error string for Neo4j failure (Exception)
# ---------------------------------------------------------------------------

def test_remember_tool_neo4j_failure():
    mock_service = MagicMock()
    mock_service.store_memory.side_effect = Exception("database down")

    result = _get_tool_fn("remember")(ctx=_ctx(mock_service), content="valid content", confidence=0.5)

    assert isinstance(result, str)
    assert "Failed to store memory" in result


# ---------------------------------------------------------------------------
# MCP server registers recall tool
# ---------------------------------------------------------------------------

def test_mcp_server_registers_recall_tool():
    from src.mcp.server import mcp
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "recall" in names
    assert "remember" in names


# ---------------------------------------------------------------------------
# recall tool returns plain-text str containing result content
# ---------------------------------------------------------------------------

def test_recall_tool_valid_input():
    memory = _make_memory()
    mock_service = MagicMock()
    mock_service.search_memory.return_value = [(memory, 0.9)]

    result = _get_tool_fn("recall")(ctx=_ctx(mock_service), query="color preferences", limit=10)

    assert isinstance(result, str)
    assert memory.content in result


# ---------------------------------------------------------------------------
# recall tool returns "No memories found" for empty results
# ---------------------------------------------------------------------------

def test_recall_tool_no_results():
    mock_service = MagicMock()
    mock_service.search_memory.return_value = []

    result = _get_tool_fn("recall")(ctx=_ctx(mock_service), query="quantum physics", limit=10)

    assert isinstance(result, str)
    assert "No memories found" in result


# ---------------------------------------------------------------------------
# recall tool returns error string for empty query (ValueError)
# ---------------------------------------------------------------------------

def test_recall_tool_empty_query_error():
    mock_service = MagicMock()
    mock_service.search_memory.side_effect = ValueError("Query cannot be empty.")

    result = _get_tool_fn("recall")(ctx=_ctx(mock_service), query="", limit=10)

    assert isinstance(result, str)
    assert "Query cannot be empty." in result


# ---------------------------------------------------------------------------
# recall tool returns error string for embedding failure (RuntimeError)
# ---------------------------------------------------------------------------

def test_recall_tool_embedding_failure():
    mock_service = MagicMock()
    mock_service.search_memory.side_effect = RuntimeError("model crashed")

    result = _get_tool_fn("recall")(ctx=_ctx(mock_service), query="valid query", limit=10)

    assert isinstance(result, str)
    assert "Failed to search memories" in result


# ---------------------------------------------------------------------------
# recall tool returns error string for Neo4j failure (Exception)
# ---------------------------------------------------------------------------

def test_recall_tool_neo4j_failure():
    mock_service = MagicMock()
    mock_service.search_memory.side_effect = Exception("database down")

    result = _get_tool_fn("recall")(ctx=_ctx(mock_service), query="valid query", limit=10)

    assert isinstance(result, str)
    assert "Failed to search memories" in result


# ---------------------------------------------------------------------------
# recall tool passes limit parameter to service
# ---------------------------------------------------------------------------

def test_recall_tool_respects_limit():
    mock_service = MagicMock()
    mock_service.search_memory.return_value = []

    _get_tool_fn("recall")(ctx=_ctx(mock_service), query="color preferences", limit=5)

    mock_service.search_memory.assert_called_once_with("color preferences", 5)


# ---------------------------------------------------------------------------
# recall tool returns error string for invalid limit (ValueError)
# ---------------------------------------------------------------------------

def test_recall_tool_invalid_limit():
    mock_service = MagicMock()
    mock_service.search_memory.side_effect = ValueError("Limit must be at least 1.")

    result = _get_tool_fn("recall")(ctx=_ctx(mock_service), query="valid query", limit=0)

    assert isinstance(result, str)
    assert "Limit must be at least 1." in result
