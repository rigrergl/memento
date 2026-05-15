"""Tests for src/mcp/server.py lifespan hook."""
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Driver must be closed even when ensure_vector_index raises
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lifespan_closes_driver_on_startup_failure():
    """repository.close must be called via asyncio.to_thread even when ensure_vector_index raises."""
    import src.mcp.server as server_module

    mock_config = MagicMock()
    mock_config.neo4j_uri = "bolt://localhost:7687"
    mock_config.neo4j_user = "neo4j"
    mock_config.neo4j_password = "password"

    mock_repo = MagicMock()
    mock_repo.ensure_vector_index = MagicMock()
    mock_repo.close = MagicMock()

    to_thread_calls = []

    async def fake_to_thread(fn, *args, **kwargs):
        to_thread_calls.append(fn)
        if fn == mock_repo.ensure_vector_index:
            raise RuntimeError("simulated index failure")

    with patch("src.mcp.server.Config", return_value=mock_config), \
         patch("src.mcp.server.Factory.create_embedder", return_value=MagicMock()), \
         patch("src.mcp.server.Neo4jRepository", return_value=mock_repo), \
         patch("asyncio.to_thread", side_effect=fake_to_thread):

        with pytest.raises(RuntimeError, match="simulated index failure"):
            async with server_module.lifespan(server_module.mcp):
                pass

    assert mock_repo.close in to_thread_calls, \
        "repository.close must be called via asyncio.to_thread even on startup failure"
    assert to_thread_calls.count(mock_repo.close) == 1


# ---------------------------------------------------------------------------
# The server module must carry no mutable state — service is injected via
# Context.lifespan_context, not via a module-level global.
# ---------------------------------------------------------------------------

def test_module_has_no_mutable_state():
    """The server module must not expose `service`, `config`, `embedder`, or `repository` as attributes."""
    import src.mcp.server as server_module

    for name in ("service", "config", "embedder", "repository"):
        assert not hasattr(server_module, name), (
            f"{name!r} must not be a module-level attribute — "
            f"per-request access is via Context.lifespan_context"
        )


# ---------------------------------------------------------------------------
# Importing the module must not instantiate Config, Neo4jRepository, or SentenceTransformer
# ---------------------------------------------------------------------------

def test_bare_import_does_not_construct_config_or_repository_or_embedder():
    """Importing src.mcp.server must not trigger Config, Neo4jRepository, or SentenceTransformer construction."""
    for key in list(sys.modules.keys()):
        if "src.mcp.server" in key:
            del sys.modules[key]

    def _boom(*args, **kwargs):
        raise AssertionError("import touched it")

    with patch("src.utils.config.Config.__init__", side_effect=_boom), \
         patch("src.graph.neo4j.Neo4jRepository.__init__", side_effect=_boom), \
         patch("src.embeddings.local_embedding_provider.SentenceTransformer", side_effect=_boom):
        import src.mcp.server  # noqa: F401


# ---------------------------------------------------------------------------
# Lifespan yields a dict containing the MemoryService under "service"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lifespan_yields_service_in_context():
    """The lifespan must yield a dict with the constructed MemoryService under the 'service' key."""
    import src.mcp.server as server_module

    mock_config = MagicMock()
    mock_config.neo4j_uri = "bolt://localhost:7687"
    mock_config.neo4j_user = "neo4j"
    mock_config.neo4j_password = "password"

    mock_embedder = MagicMock()
    mock_repo = MagicMock()
    mock_service = MagicMock()

    with patch("src.mcp.server.Config", return_value=mock_config), \
         patch("src.mcp.server.Factory.create_embedder", return_value=mock_embedder), \
         patch("src.mcp.server.Neo4jRepository", return_value=mock_repo), \
         patch("src.mcp.server.MemoryService", return_value=mock_service), \
         patch("asyncio.to_thread", new_callable=AsyncMock):

        async with server_module.lifespan(server_module.mcp) as context:
            assert isinstance(context, dict)
            assert context["service"] is mock_service


# ---------------------------------------------------------------------------
# Lifespan calls ensure_vector_index exactly once
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lifespan_calls_ensure_vector_index_once():
    """lifespan __aenter__ calls repository.ensure_vector_index exactly once."""
    import src.mcp.server as server_module

    mock_config = MagicMock()
    mock_config.neo4j_uri = "bolt://localhost:7687"
    mock_config.neo4j_user = "neo4j"
    mock_config.neo4j_password = "password"

    mock_embedder = MagicMock()
    mock_repo = MagicMock()
    mock_repo.ensure_vector_index = MagicMock()
    mock_repo.close = MagicMock()
    mock_service = MagicMock()

    with patch("src.mcp.server.Config", return_value=mock_config), \
         patch("src.mcp.server.Factory.create_embedder", return_value=mock_embedder), \
         patch("src.mcp.server.Neo4jRepository", return_value=mock_repo), \
         patch("src.mcp.server.MemoryService", return_value=mock_service), \
         patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:

        async with server_module.lifespan(server_module.mcp):
            pass

        calls = mock_to_thread.call_args_list
        ensure_calls = [c for c in calls if c.args and c.args[0] == mock_repo.ensure_vector_index]
        assert len(ensure_calls) == 1


# ---------------------------------------------------------------------------
# Lifespan __aexit__ closes the repository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lifespan_aexit_closes_repository():
    """lifespan __aexit__ calls repository.close."""
    import src.mcp.server as server_module

    mock_config = MagicMock()
    mock_config.neo4j_uri = "bolt://localhost:7687"
    mock_config.neo4j_user = "neo4j"
    mock_config.neo4j_password = "password"

    mock_embedder = MagicMock()
    mock_repo = MagicMock()
    mock_repo.ensure_vector_index = MagicMock()
    mock_repo.close = MagicMock()
    mock_service = MagicMock()

    with patch("src.mcp.server.Config", return_value=mock_config), \
         patch("src.mcp.server.Factory.create_embedder", return_value=mock_embedder), \
         patch("src.mcp.server.Neo4jRepository", return_value=mock_repo), \
         patch("src.mcp.server.MemoryService", return_value=mock_service), \
         patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:

        async with server_module.lifespan(server_module.mcp):
            pass

        calls = mock_to_thread.call_args_list
        close_calls = [c for c in calls if c.args and c.args[0] == mock_repo.close]
        assert len(close_calls) == 1
