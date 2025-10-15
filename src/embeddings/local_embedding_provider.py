"""Local embedding provider using sentence-transformers."""
from sentence_transformers import SentenceTransformer
from src.embeddings.base import IEmbeddingProvider


class LocalEmbeddingProvider(IEmbeddingProvider):
    """
    Local embedding provider using sentence-transformers library.

    This provider runs models locally without requiring API calls,
    making it suitable for offline use and avoiding API costs.

    Args:
        model_name: Name of the sentence-transformers model to use
        cache_dir: Directory to cache downloaded models
    """

    def __init__(self, model_name: str, cache_dir: str):
        """
        Initialize the local embedding provider.

        Args:
            model_name: Name of the sentence-transformers model
            cache_dir: Directory for model cache
        """
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._model = SentenceTransformer(model_name, cache_folder=cache_dir)
        self._dimension = self._model.get_sentence_embedding_dimension()

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def dimension(self) -> int:
        """
        Get the dimensionality of embeddings produced by this provider.

        Returns:
            The number of dimensions in the embedding vectors
        """
        return self._dimension
