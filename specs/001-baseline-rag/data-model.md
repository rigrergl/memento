# Data Model: Baseline RAG - Store Memory

**Date**: 2025-12-24
**Feature**: Store memory as Memory with vector embedding

## Overview

This document defines the data structures for the baseline RAG feature. The model uses the existing `Memory` class from `src/models/memory.py`, keeping all fields with `source` defaulting to `"user_requested"` and supersession fields defaulting to `None`.

## Core Entity: Memory

### Description
A Memory represents a single stored memory - the raw text from a user along with its vector embedding for future semantic search. For baseline RAG, `source` defaults to `"user_requested"` (only explicit user-requested memories are created) and supersession fields default to `None` (no supersession logic yet).

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `id` | string (UUID) | Yes | Unique identifier for the memory | Valid UUID v4 format |
| `content` | string | Yes | The exact memory text from the user | 1-4000 characters (configurable max) |
| `embedding` | list[float] | Yes | 384-dimensional vector embedding | Exactly 384 floats |
| `confidence` | float | Yes | Confidence score for this memory (0-1 scale) | Float between 0.0 and 1.0 |
| `created_at` | datetime | Yes | Timestamp when memory was created | ISO 8601 format |
| `updated_at` | datetime | Yes | Timestamp of last modification | ISO 8601 format |
| `accessed_at` | datetime | Yes | Timestamp of last retrieval | ISO 8601 format |
| `source` | string | No (default: `"user_requested"`) | How the memory was created | `"user_requested"` or `"auto_captured"` |
| `supersedes` | string (UUID) or null | No (default: `null`) | ID of memory this replaces | Valid UUID v4 or null |
| `superseded_by` | string (UUID) or null | No (default: `null`) | ID of memory that replaces this | Valid UUID v4 or null |

**Note**: The field `content` stores the exact words from the user.

### Validation Rules

**content validation (applied in service layer):**
- MUST NOT be empty string
- MUST NOT be whitespace-only
- MUST NOT exceed `max_memory_length` config value (default: 4000)

**confidence validation (applied in service layer):**
- MUST be a float between 0.0 and 1.0 (inclusive)
- Higher values indicate higher reliability/certainty of the memory
- Lower values indicate uncertain or tentative memories

**id validation:**
- MUST be valid UUID v4 string
- Generated using Python's `uuid.uuid4()`

**timestamp validation:**
- All timestamps MUST be valid ISO 8601 datetime
- `created_at`: Set on creation using `datetime.now(timezone.utc)`
- `updated_at`: Initially same as `created_at`; updated on modifications (future feature)
- `accessed_at`: Initially same as `created_at`; updated on retrieval (future feature)

### State Transitions

Memory lifecycle for baseline implementation:
```
[Created] ─────> [Persisted]
```

Future features may add:
- Update state (modify `updated_at`)
- Access tracking (modify `accessed_at`)

## Python Dataclass

**File**: `src/models/memory.py` (keep existing file, set `source` default)

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Memory:
    """
    Represents a stored memory in the baseline RAG system.

    Attributes:
        id: Unique UUID identifier (as string)
        content: The exact memory text from the user
        embedding: 384-dimensional vector embedding
        confidence: Confidence score (0-1 scale, higher = more reliable)
        created_at: Timestamp when memory was created
        updated_at: Timestamp of last modification
        accessed_at: Timestamp of last retrieval
        source: How the memory was created (defaults to 'user_requested')
        supersedes: ID of memory this replaces (None for baseline RAG)
        superseded_by: ID of memory that replaces this (None for baseline RAG)
    """
    id: str
    content: str
    embedding: list[float]
    confidence: float  # 0.0 to 1.0, higher values = more reliable/certain
    created_at: datetime
    updated_at: datetime
    accessed_at: datetime
    source: str = "user_requested"
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
```

## Neo4j Node Representation

### Node Label
`Memory`

### Node Properties

```cypher
(:Memory {
  id: "550e8400-e29b-41d4-a716-446655440000",  // UUID string
  content: "My favorite color is blue",         // Text content
  embedding: [0.123, -0.456, ...],              // 384 floats
  confidence: 0.85,                              // Float 0.0-1.0
  created_at: "2025-12-24T10:30:00Z",          // ISO 8601 datetime
  updated_at: "2025-12-24T10:30:00Z",          // ISO 8601 datetime
  accessed_at: "2025-12-24T10:30:00Z",         // ISO 8601 datetime
  source: "user_requested",                     // Always this value for baseline RAG
  supersedes: null,                             // null for baseline RAG
  superseded_by: null                           // null for baseline RAG
})
```

### Neo4j Constraints

**Uniqueness constraint on id:**
```cypher
CREATE CONSTRAINT memory_id_unique IF NOT EXISTS
FOR (m:Memory)
REQUIRE m.id IS UNIQUE
```

**Vector index on embedding:**
```cypher
CREATE VECTOR INDEX memory_embedding_index IF NOT EXISTS
FOR (m:Memory)
ON m.embedding
OPTIONS { indexConfig: {
  `vector.dimensions`: 384,
  `vector.similarity_function`: 'cosine'
}}
```

## Relationships

None. Baseline RAG has no graph relationships (out of scope).

Future features may add:
- `SUPERSEDES` relationship (for memory updates)
- `RELATES_TO` relationship (for connected memories)
- Entity extraction with subject-predicate-object triples

## Configuration Model

Extension to existing `Config` class in `src/utils/config.py`:

```python
class Config(BaseSettings):
    # ... existing fields ...

    # Memory validation
    max_memory_length: int = Field(
        default=4000,
        ge=1,
        le=100000,
        description="Maximum allowed memory text length in characters"
    )

    # MCP Server
    mcp_host: str = Field(
        default="0.0.0.0",
        description="MCP server host address"
    )
    mcp_port: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="MCP server port number"
    )
```

## Error Handling

Errors use standard Python exceptions — no custom exception classes:

- **Validation failures** (empty content, exceeds max length, invalid confidence, empty query): raise `ValueError` with a human-readable message. The MCP tool catches `ValueError` and returns `str(e)` as a plain-text error to the client.
- **Embedding provider failures**: the underlying exception (e.g., `RuntimeError`) propagates from the provider up through the service layer. The MCP tool catches it and returns a generic plain-text error string.
- **Neo4j failures**: the underlying exception (e.g., `neo4j.exceptions.ServiceUnavailable`) propagates from the repository up through the service layer. The MCP tool catches it and returns a generic plain-text error string.

**Example validation errors:**
```python
raise ValueError("Memory text cannot be empty.")
raise ValueError(f"Memory text exceeds maximum length of {max_length} characters")
raise ValueError("Confidence must be between 0.0 and 1.0")
raise ValueError("Query cannot be empty.")
```

## Data Flow

```
User Input (content string, confidence float)
    ↓
[Validation: length, whitespace, confidence range]
    ↓
[Embedding Generation: IEmbeddingProvider]
    ↓
[Memory Creation: id, content, embedding, confidence, timestamps]
    ↓
[Neo4j Persistence: create node, ensure index]
    ↓
Confirmation Response (memory id)
```

## Example Data

**Valid Memory:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "My favorite color is blue",
  "embedding": [0.123, -0.456, 0.789, ... ],  // 384 floats
  "confidence": 0.85,
  "created_at": "2025-12-24T10:30:00+00:00",
  "updated_at": "2025-12-24T10:30:00+00:00",
  "accessed_at": "2025-12-24T10:30:00+00:00",
  "source": "user_requested",
  "supersedes": null,
  "superseded_by": null
}
```

**Invalid Inputs:**
```python
# Too short
content = ""  # ValidationError: empty

# Too long
content = "x" * 5000  # ValidationError: exceeds 4000 (if default config)

# Whitespace only
content = "   \n\t   "  # ValidationError: whitespace-only

# Invalid confidence
confidence = -0.1  # ValidationError: must be >= 0.0
confidence = 1.5  # ValidationError: must be <= 1.0
```

## Design Decisions

### Why keep source, supersedes, superseded_by?
These fields exist in the original `Memory` dataclass and will be used in future specs (knowledge graph extraction, memory supersession). Keeping them now with safe defaults (`source = "user_requested"`, supersession fields = `None`) avoids a later model migration and keeps the source of truth intact for future re-processing.

### Why keep confidence, updated_at, accessed_at?
These fields provide valuable metadata without adding complexity. `confidence` allows LLMs to indicate memory certainty. Timestamps enable future audit capabilities.

### Why confidence scale 0-1?
Standard normalized scale that's familiar to ML/AI systems and LLMs. Maps naturally to probability/certainty concepts and integrates well with other confidence scores.

### Why UUID over auto-increment?
UUIDs are standard for distributed systems and avoid race conditions. Neo4j doesn't have native auto-increment, so UUIDs are simpler.

### Why 384 dimensions?
The existing `LocalEmbeddingProvider` uses `all-MiniLM-L6-v2` which produces 384-dimensional embeddings. This is hardcoded to match the model. If the embedding model changes, the vector index must be rebuilt with the correct dimension.

### Why is the similarity metric hardcoded (not configurable)?
Neo4j bakes the similarity function into the vector index at creation time. There is no way to change it without dropping and recreating the index (which would require re-embedding all stored memories). Making it a runtime config value would create the illusion of control that doesn't exist. Cosine similarity is the correct default for text embedding similarity. See TD-002 for the remediation plan if this ever needs to change.

### Why no update/delete?
Baseline RAG is write-only. Update and delete operations add complexity without current use cases (YAGNI). The `updated_at` and `accessed_at` fields are placeholders for future features.

### Why datetime instead of timestamp?
Python's `datetime` is more expressive and Neo4j has native datetime support. ISO 8601 format ensures timezone handling.
