"""Tests for Factory class."""
import pytest
from src.utils.config import Config
from src.utils.factory import Factory
from src.embeddings.base import IEmbeddingProvider
from src.embeddings.local_embedding_provider import LocalEmbeddingProvider


class TestFactory:
    """Test Factory class for creating providers."""

    def test_create_embedder_with_local_provider(self, monkeypatch):
        """Test that Factory creates LocalEmbeddingProvider when provider is 'local'."""
        # Set up config for local provider
        monkeypatch.setenv("MEMENTO_EMBEDDING_PROVIDER", "local")
        monkeypatch.setenv("MEMENTO_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        monkeypatch.setenv("MEMENTO_EMBEDDING_CACHE_DIR", ".cache/models")
        monkeypatch.setenv("MEMENTO_NEO4J_URI", "neo4j+s://test.databases.neo4j.io")
        monkeypatch.setenv("MEMENTO_NEO4J_USER", "neo4j")
        monkeypatch.setenv("MEMENTO_NEO4J_PASSWORD", "password")

        config = Config()
        provider = Factory.create_embedder(config)

        assert isinstance(provider, LocalEmbeddingProvider)
        assert isinstance(provider, IEmbeddingProvider)

    def test_create_embedder_uses_config_values(self, monkeypatch):
        """Test that Factory passes config values to provider."""
        monkeypatch.setenv("MEMENTO_EMBEDDING_PROVIDER", "local")
        monkeypatch.setenv("MEMENTO_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        monkeypatch.setenv("MEMENTO_EMBEDDING_CACHE_DIR", ".cache/test")
        monkeypatch.setenv("MEMENTO_NEO4J_URI", "neo4j+s://test.databases.neo4j.io")
        monkeypatch.setenv("MEMENTO_NEO4J_USER", "neo4j")
        monkeypatch.setenv("MEMENTO_NEO4J_PASSWORD", "password")

        config = Config()
        provider = Factory.create_embedder(config)

        # Verify provider works (implying config was passed correctly)
        embedding = provider.generate_embedding("test")
        assert isinstance(embedding, list)
        assert len(embedding) == 384

    def test_create_embedder_unsupported_provider(self, monkeypatch):
        """Test that Factory raises ValueError for unsupported providers."""
        monkeypatch.setenv("MEMENTO_EMBEDDING_PROVIDER", "unsupported")
        monkeypatch.setenv("MEMENTO_EMBEDDING_MODEL", "some-model")
        monkeypatch.setenv("MEMENTO_EMBEDDING_CACHE_DIR", ".cache/models")
        monkeypatch.setenv("MEMENTO_NEO4J_URI", "neo4j+s://test.databases.neo4j.io")
        monkeypatch.setenv("MEMENTO_NEO4J_USER", "neo4j")
        monkeypatch.setenv("MEMENTO_NEO4J_PASSWORD", "password")

        config = Config()

        with pytest.raises(ValueError, match="Unsupported provider"):
            Factory.create_embedder(config)

    def test_factory_integration_end_to_end(self, monkeypatch):
        """Test end-to-end: Config → Factory → Provider → Embedding."""
        # Set all required env vars for local provider
        monkeypatch.setenv("MEMENTO_EMBEDDING_PROVIDER", "local")
        monkeypatch.setenv("MEMENTO_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        monkeypatch.setenv("MEMENTO_EMBEDDING_CACHE_DIR", ".cache/models")
        monkeypatch.setenv("MEMENTO_NEO4J_URI", "neo4j+s://test.databases.neo4j.io")
        monkeypatch.setenv("MEMENTO_NEO4J_USER", "neo4j")
        monkeypatch.setenv("MEMENTO_NEO4J_PASSWORD", "password")

        # Create config and provider
        config = Config()
        provider = Factory.create_embedder(config)

        # Generate embedding
        text = "End-to-end integration test"
        embedding = provider.generate_embedding(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert provider.dimension() == 384


# Need to import os for env var clearing in integration test
import os
