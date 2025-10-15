"""Base interface for embedding providers."""
from abc import ABC, abstractmethod


class IEmbeddingProvider(ABC):
    """
    Interface for embedding providers.

    Embedding providers convert text into vector representations (embeddings)
    for semantic search and similarity comparisons.
    """

    @abstractmethod
    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        pass

    @abstractmethod
    def dimension(self) -> int:
        """
        Get the dimensionality of embeddings produced by this provider.

        Returns:
            The number of dimensions in the embedding vectors
        """
        pass
