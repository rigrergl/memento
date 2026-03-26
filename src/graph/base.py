"""Base interface for graph repository."""
from abc import ABC, abstractmethod

from src.models.memory import Memory


class IGraphRepository(ABC):
    """Interface for graph database operations on Memory nodes."""

    @abstractmethod
    def create_memory(self, memory: Memory) -> None:
        """Persist a Memory node to the graph database."""
        pass

    @abstractmethod
    def ensure_vector_index(self) -> None:
        """Create vector index and uniqueness constraint if they do not exist."""
        pass

    @abstractmethod
    def search_memories(self, embedding: list[float], limit: int) -> list[tuple[Memory, float]]:
        """Search memories by vector similarity, returning (Memory, score) pairs ordered by score."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""
        pass
