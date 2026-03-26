"""Fixtures for MCP server tests: patch external dependencies so server.py imports cleanly."""
import os
from unittest.mock import MagicMock, patch

import pytest

# Set required env vars before any Config() is instantiated during collection.
os.environ.setdefault("MEMENTO_EMBEDDING_PROVIDER", "local")
os.environ.setdefault("MEMENTO_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
os.environ.setdefault("MEMENTO_EMBEDDING_CACHE_DIR", ".cache/models")
os.environ.setdefault("MEMENTO_NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("MEMENTO_NEO4J_USER", "neo4j")
os.environ.setdefault("MEMENTO_NEO4J_PASSWORD", "password")


@pytest.fixture(scope="package", autouse=True)
def patch_server_imports():
    """Patch Neo4j driver and SentenceTransformer so server.py can be imported without real services."""
    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension.return_value = 384
    mock_driver = MagicMock()

    with patch("src.embeddings.local_embedding_provider.SentenceTransformer", return_value=mock_model), \
         patch("src.graph.neo4j.GraphDatabase") as mock_gdb:
        mock_gdb.driver.return_value = mock_driver
        yield
