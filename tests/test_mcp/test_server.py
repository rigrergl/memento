"""Tests for MCP server tools: remember and recall (T027-T035, T073-T079, T090)."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

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


# ---------------------------------------------------------------------------
# T027: MCP server registers remember tool
# ---------------------------------------------------------------------------

def test_mcp_server_registers_remember_tool():
    """T027: Verify remember tool is registered on the MCP server."""
    from src.mcp.server import mcp
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "remember" in names


# ---------------------------------------------------------------------------
# T028: remember tool returns plain-text str containing "Memory stored with id:"
# ---------------------------------------------------------------------------

def test_remember_tool_valid_input():
    """T028: Mock service, verify response is plain-text str containing 'Memory stored with id:'."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.store_memory.return_value = _make_memory()

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("remember")(content="My favorite color is blue", confidence=0.85)

    assert isinstance(result, str)
    assert "Memory stored with id:" in result


# ---------------------------------------------------------------------------
# T029: remember tool returns memory UUID in response
# ---------------------------------------------------------------------------

def test_remember_tool_returns_memory_id():
    """T029: Mock service returning Memory with known UUID, verify UUID in plain-text response."""
    from src.mcp import server as server_module

    memory = _make_memory(id="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    mock_service = MagicMock()
    mock_service.store_memory.return_value = memory

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("remember")(content="My favorite color is blue", confidence=0.85)

    assert "a1b2c3d4-e5f6-7890-abcd-ef1234567890" in result


# ---------------------------------------------------------------------------
# T030: remember tool return type is str
# ---------------------------------------------------------------------------

def test_remember_tool_returns_str_type():
    """T030: Mock service, verify return type is str (guards against returning dict)."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.store_memory.return_value = _make_memory()

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("remember")(content="valid content", confidence=0.5)

    assert type(result) is str


# ---------------------------------------------------------------------------
# T031: remember tool returns error string for empty memory (ValueError)
# ---------------------------------------------------------------------------

def test_remember_tool_empty_memory_error():
    """T031: Mock service to raise ValueError, verify error string returned (not raised)."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.store_memory.side_effect = ValueError("Memory text cannot be empty.")

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("remember")(content="", confidence=0.5)

    assert isinstance(result, str)
    assert "Memory text cannot be empty." in result


# ---------------------------------------------------------------------------
# T032: remember tool returns error string for exceeds max length (ValueError)
# ---------------------------------------------------------------------------

def test_remember_tool_exceeds_max_length_error():
    """T032: Mock service to raise ValueError for max length, verify error string returned."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.store_memory.side_effect = ValueError("Memory text exceeds maximum length of 4000 characters")

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("remember")(content="x" * 5000, confidence=0.5)

    assert isinstance(result, str)
    assert "exceeds" in result.lower() or "length" in result.lower()


# ---------------------------------------------------------------------------
# T033: remember tool returns error string for invalid confidence (ValueError)
# ---------------------------------------------------------------------------

def test_remember_tool_invalid_confidence_error():
    """T033: Mock service to raise ValueError for invalid confidence, verify error string returned."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.store_memory.side_effect = ValueError("Confidence must be between 0.0 and 1.0")

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("remember")(content="valid content", confidence=1.5)

    assert isinstance(result, str)
    assert "confidence" in result.lower() or "0.0" in result


# ---------------------------------------------------------------------------
# T034: remember tool returns error string for embedding failure (RuntimeError)
# ---------------------------------------------------------------------------

def test_remember_tool_embedding_failure():
    """T034: Mock service to raise RuntimeError, verify error string returned (not raised)."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.store_memory.side_effect = RuntimeError("model crashed")

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("remember")(content="valid content", confidence=0.5)

    assert isinstance(result, str)
    assert "Failed to store memory" in result


# ---------------------------------------------------------------------------
# T035: remember tool returns error string for Neo4j failure (Exception)
# ---------------------------------------------------------------------------

def test_remember_tool_neo4j_failure():
    """T035: Mock service to raise Exception, verify error string returned (not raised)."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.store_memory.side_effect = Exception("database down")

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("remember")(content="valid content", confidence=0.5)

    assert isinstance(result, str)
    assert "Failed to store memory" in result


# ---------------------------------------------------------------------------
# T073: MCP server registers recall tool
# ---------------------------------------------------------------------------

def test_mcp_server_registers_recall_tool():
    """T073: Verify recall tool is registered alongside remember tool."""
    from src.mcp.server import mcp
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "recall" in names
    assert "remember" in names


# ---------------------------------------------------------------------------
# T074: recall tool returns plain-text str containing result content
# ---------------------------------------------------------------------------

def test_recall_tool_valid_input():
    """T074: Mock service returning [(mock_memory, 0.9)], verify response is plain-text str containing result content."""
    from src.mcp import server as server_module

    memory = _make_memory()
    mock_service = MagicMock()
    mock_service.search_memory.return_value = [(memory, 0.9)]

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("recall")(query="color preferences", limit=10)

    assert isinstance(result, str)
    assert memory.content in result


# ---------------------------------------------------------------------------
# T075: recall tool returns "No memories found" for empty results
# ---------------------------------------------------------------------------

def test_recall_tool_no_results():
    """T075: Mock service returning empty list, verify response contains 'No memories found'."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.search_memory.return_value = []

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("recall")(query="quantum physics", limit=10)

    assert isinstance(result, str)
    assert "No memories found" in result


# ---------------------------------------------------------------------------
# T076: recall tool returns error string for empty query (ValueError)
# ---------------------------------------------------------------------------

def test_recall_tool_empty_query_error():
    """T076: Mock service to raise ValueError, verify error string returned (not raised)."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.search_memory.side_effect = ValueError("Query cannot be empty.")

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("recall")(query="", limit=10)

    assert isinstance(result, str)
    assert "Query cannot be empty." in result


# ---------------------------------------------------------------------------
# T077: recall tool returns error string for embedding failure (RuntimeError)
# ---------------------------------------------------------------------------

def test_recall_tool_embedding_failure():
    """T077: Mock service to raise RuntimeError, verify error string returned (not raised)."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.search_memory.side_effect = RuntimeError("model crashed")

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("recall")(query="valid query", limit=10)

    assert isinstance(result, str)
    assert "Failed to search memories" in result


# ---------------------------------------------------------------------------
# T078: recall tool returns error string for Neo4j failure (Exception)
# ---------------------------------------------------------------------------

def test_recall_tool_neo4j_failure():
    """T078: Mock service to raise Exception, verify error string returned (not raised)."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.search_memory.side_effect = Exception("database down")

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("recall")(query="valid query", limit=10)

    assert isinstance(result, str)
    assert "Failed to search memories" in result


# ---------------------------------------------------------------------------
# T079: recall tool passes limit parameter to service
# ---------------------------------------------------------------------------

def test_recall_tool_respects_limit():
    """T079: Mock service, verify limit parameter passed through to service.search_memory."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.search_memory.return_value = []

    with patch.object(server_module, "service", mock_service):
        _get_tool_fn("recall")(query="color preferences", limit=5)

    mock_service.search_memory.assert_called_once_with("color preferences", 5)


# ---------------------------------------------------------------------------
# T090: recall tool returns error string for invalid limit (ValueError)
# ---------------------------------------------------------------------------

def test_recall_tool_invalid_limit():
    """T090: Mock service to raise ValueError for limit=0, verify error string returned (not raised)."""
    from src.mcp import server as server_module

    mock_service = MagicMock()
    mock_service.search_memory.side_effect = ValueError("Limit must be at least 1.")

    with patch.object(server_module, "service", mock_service):
        result = _get_tool_fn("recall")(query="valid query", limit=0)

    assert isinstance(result, str)
    assert "Limit must be at least 1." in result
