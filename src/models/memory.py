"""Memory domain model representing a stored memory/fact in the system."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Memory:
    """
    Represents a single memory/fact stored in the system.

    Attributes:
        id: Unique identifier for the memory
        content: The actual memory content in natural language
        embedding: Vector embedding for semantic search
        confidence: Confidence score (0-1)
        source: How the memory was created ('explicit' or 'extracted')
        supersedes: ID of memory this replaces (if any)
        superseded_by: ID of memory that replaces this (if any)
        created_at: Timestamp when memory was created
        updated_at: Timestamp of last modification
        accessed_at: Timestamp of last retrieval
    """

    id: str
    content: str
    embedding: list[float]
    confidence: float
    source: str  # 'explicit' | 'extracted'
    created_at: datetime
    updated_at: datetime
    accessed_at: datetime
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
