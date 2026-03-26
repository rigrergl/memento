"""MemoryService: core business logic for storing and searching memories."""
import uuid
from datetime import datetime, timezone

from src.embeddings.base import IEmbeddingProvider
from src.graph.base import IGraphRepository
from src.models.memory import Memory
from src.utils.config import Config


class MemoryService:
    """Orchestrates memory storage and semantic search."""

    def __init__(self, config: Config, embedder: IEmbeddingProvider, repository: IGraphRepository) -> None:
        self._config = config
        self._embedder = embedder
        self._repository = repository

    def _validate_content(self, content: str) -> None:
        if not content or not content.strip():
            raise ValueError("Memory text cannot be empty.")
        if len(content) > self._config.max_memory_length:
            raise ValueError(
                f"Memory text exceeds maximum length of {self._config.max_memory_length} characters "
                f"(got {len(content)})."
            )

    def _validate_confidence(self, confidence: float) -> None:
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"Invalid confidence value {confidence}: must be between 0.0 and 1.0."
            )

    def _validate_query(self, query: str) -> None:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

    def store_memory(self, content: str, confidence: float) -> Memory:
        """Validate, embed, and persist a memory. Returns the created Memory."""
        self._validate_content(content)
        self._validate_confidence(confidence)

        embedding = self._embedder.generate_embedding(content)
        now = datetime.now(timezone.utc)
        memory = Memory(
            id=str(uuid.uuid4()),
            content=content,
            embedding=embedding,
            confidence=confidence,
            created_at=now,
            updated_at=now,
            accessed_at=now,
        )
        self._repository.create_memory(memory)
        return memory

    def search_memory(self, query: str, limit: int) -> list[tuple[Memory, float]]:
        """Validate query, embed it, and return matching (Memory, score) pairs."""
        self._validate_query(query)
        if limit < 1:
            raise ValueError("Limit must be at least 1.")
        embedding = self._embedder.generate_embedding(query)
        return self._repository.search_memories(embedding, limit)
