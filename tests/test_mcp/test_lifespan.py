"""Tests for src/mcp/server.py lifespan hook (T005-T008)."""
import importlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# T005: Bare import must not instantiate Config, Neo4jRepository, or SentenceTransformer
# ---------------------------------------------------------------------------

def test_bare_import_does_not_construct_config_or_repository_or_embedder():
    """T005: Importing src.mcp.server must not trigger Config, Neo4jRepository, or SentenceTransformer construction."""
    # Remove the module from sys.modules so the import runs fresh
    for key in list(sys.modules.keys()):
        if "src.mcp.server" in key:
            del sys.modules[key]

    def _boom(*args, **kwargs):
        raise AssertionError("import touched it")

    with patch("src.utils.config.Config.__init__", side_effect=_boom), \
         patch("src.graph.neo4j.Neo4jRepository.__init__", side_effect=_boom), \
         patch("src.embeddings.local_embedding_provider.SentenceTransformer", side_effect=_boom):
        # Import must succeed — the patches ensure it would fail if touched
        import src.mcp.server  # noqa: F401


# ---------------------------------------------------------------------------
# T006: Lifespan populates module-level globals
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lifespan_populates_module_globals():
    """T006: After entering the lifespan context, config/embedder/repository/service are non-None."""
    import src.mcp.server as server_module

    mock_config = MagicMock()
    mock_config.neo4j_uri = "bolt://localhost:7687"
    mock_config.neo4j_user = "neo4j"
    mock_config.neo4j_password = "password"
    mock_config.embedding_provider = "local"
    mock_config.embedding_model = "all-MiniLM-L6-v2"
    mock_config.embedding_cache_dir = ".cache/models"

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
            assert server_module.config is not None
            assert server_module.embedder is not None
            assert server_module.repository is not None
            assert server_module.service is not None


# ---------------------------------------------------------------------------
# T007: Lifespan calls ensure_vector_index exactly once
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lifespan_calls_ensure_vector_index_once():
    """T007: lifespan __aenter__ calls repository.ensure_vector_index exactly once."""
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

        # to_thread should have been called with ensure_vector_index (first call)
        calls = mock_to_thread.call_args_list
        ensure_calls = [c for c in calls if c.args and c.args[0] == mock_repo.ensure_vector_index]
        assert len(ensure_calls) == 1


# ---------------------------------------------------------------------------
# T008: Lifespan __aexit__ closes the repository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lifespan_aexit_closes_repository():
    """T008: lifespan __aexit__ calls repository.close."""
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

        # to_thread should have been called with close on exit
        calls = mock_to_thread.call_args_list
        close_calls = [c for c in calls if c.args and c.args[0] == mock_repo.close]
        assert len(close_calls) == 1
