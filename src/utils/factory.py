"""Factory for creating embedding providers."""
from src.utils.config import Config
from src.embeddings.base import IEmbeddingProvider
from src.embeddings.local_embedding_provider import LocalEmbeddingProvider


class Factory:
    """
    Factory for creating embedding providers based on configuration.

    This factory uses a simple if/elif pattern (YAGNI) to instantiate
    providers. When more providers are added, this can be refactored
    to a more sophisticated pattern.
    """

    @staticmethod
    def create_embedder(config: Config) -> IEmbeddingProvider:
        """
        Create an embedding provider based on configuration.

        Args:
            config: Application configuration

        Returns:
            An instance of IEmbeddingProvider

        Raises:
            ValueError: If the provider specified in config is not supported
        """
        if config.embedding_provider == "local":
            return LocalEmbeddingProvider(
                model_name=config.embedding_model,
                cache_dir=config.embedding_cache_dir
            )

        raise ValueError(
            f"Unsupported provider: {config.embedding_provider}. "
            f"Supported providers: local"
        )
