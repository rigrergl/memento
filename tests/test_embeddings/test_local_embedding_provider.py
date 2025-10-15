"""Tests for LocalEmbeddingProvider."""
import pytest
from src.embeddings.base import IEmbeddingProvider
from src.embeddings.local_embedding_provider import LocalEmbeddingProvider


class TestLocalEmbeddingProvider:
    """Test LocalEmbeddingProvider implementation."""

    @pytest.fixture
    def provider(self):
        """Create a LocalEmbeddingProvider instance for testing."""
        return LocalEmbeddingProvider(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            cache_dir=".cache/models"
        )

    def test_implements_interface(self, provider):
        """Test that LocalEmbeddingProvider implements IEmbeddingProvider."""
        assert isinstance(provider, IEmbeddingProvider)

    def test_constructor_injection(self):
        """Test that constructor accepts model_name and cache_dir parameters."""
        # Use a real model to verify constructor parameters work
        custom_provider = LocalEmbeddingProvider(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            cache_dir=".cache/test-models"
        )
        assert custom_provider is not None
        # Verify it can generate embeddings with custom cache_dir
        embedding = custom_provider.generate_embedding("test")
        assert len(embedding) == 384

    def test_generate_embedding_returns_list(self, provider):
        """Test that generate_embedding returns a list of floats."""
        text = "Hello, world!"
        embedding = provider.generate_embedding(text)

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    def test_embedding_dimensions(self, provider):
        """Test that embeddings have correct dimensions for all-MiniLM-L6-v2 model."""
        text = "Test embedding dimensions"
        embedding = provider.generate_embedding(text)

        # all-MiniLM-L6-v2 produces 384-dimensional embeddings
        assert len(embedding) == 384

    def test_dimension_property(self, provider):
        """Test that dimension() property returns correct value."""
        assert provider.dimension() == 384

    def test_embedding_consistency(self, provider):
        """Test that same text produces same embedding."""
        text = "Consistent embedding test"

        embedding1 = provider.generate_embedding(text)
        embedding2 = provider.generate_embedding(text)

        assert embedding1 == embedding2

    def test_different_text_different_embeddings(self, provider):
        """Test that different texts produce different embeddings."""
        text1 = "First text"
        text2 = "Second text"

        embedding1 = provider.generate_embedding(text1)
        embedding2 = provider.generate_embedding(text2)

        assert embedding1 != embedding2

    def test_empty_string(self, provider):
        """Test handling of empty string."""
        embedding = provider.generate_embedding("")

        assert isinstance(embedding, list)
        assert len(embedding) == 384

    def test_long_text(self, provider):
        """Test handling of very long text."""
        long_text = "This is a test sentence. " * 1000  # ~5000 words

        embedding = provider.generate_embedding(long_text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384

    def test_unicode_text(self, provider):
        """Test handling of unicode characters."""
        unicode_text = "Hello 世界 🌍"

        embedding = provider.generate_embedding(unicode_text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384
