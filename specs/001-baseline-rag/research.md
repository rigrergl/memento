# Research: Baseline RAG - Store Memory

**Date**: 2025-12-24
**Feature**: Store memory as Memory node with vector embedding in Neo4j via MCP HTTP server

## Overview

This document consolidates research findings for the technical decisions required to implement the baseline RAG feature. All decisions prioritize YAGNI/KISS principles while leveraging existing infrastructure.

## Decision 1: Neo4j Vector Index Configuration

### Decision
Use Neo4j vector indexes with the following configuration:
- **Dimensions**: 384 (matches `all-MiniLM-L6-v2` model from existing tests)
- **Similarity Function**: `cosine` (standard for sentence-transformers models)
- **Index Creation**: Idempotent creation using `IF NOT EXISTS` clause
- **Index Name**: `memory_embedding_index`

### Rationale
The existing `LocalEmbeddingProvider` uses `all-MiniLM-L6-v2` which produces 384-dimensional embeddings (confirmed in `tests/test_embeddings/test_local_embedding_provider.py:49`). Cosine similarity is the standard for sentence-transformers models and measures semantic similarity effectively.

### Implementation Pattern

**Create Index (Cypher):**
```cypher
CREATE VECTOR INDEX memory_embedding_index IF NOT EXISTS
FOR (m:Memory)
ON m.embedding
OPTIONS { indexConfig: {
  `vector.dimensions`: 384,
  `vector.similarity_function`: 'cosine'
}}
```

**Check Index Status (Cypher):**
```cypher
SHOW VECTOR INDEXES YIELD name, state, populationPercent
WHERE name = 'memory_embedding_index'
```

### Key Considerations
- Vector indexes are approximate nearest neighbor (not exact), which is acceptable for RAG
- Index state transitions: `POPULATING` → `ONLINE` (must wait for ONLINE before queries)
- Dimension mismatch returns errors, so strict validation at 384 dimensions is critical
- Use explicit index names for clarity (avoid auto-generated names)

### Alternatives Considered
- **Euclidean similarity**: Rejected because cosine is standard for sentence embeddings and measures angle (semantic similarity) rather than distance
- **Different dimensions**: Rejected to maintain compatibility with existing embedding model
- **No index initially**: Rejected because vector index is core requirement (FR-005)

### References
- [Neo4j Vector Indexes Documentation](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/)

---

## Decision 2: FastMCP HTTP Transport Configuration

### Decision
Expose MCP server via HTTP transport using FastMCP's `run()` method with:
- **Transport**: `http`
- **Port**: 8000 (configurable via environment)
- **Host**: `0.0.0.0` (allow external connections)
- **Endpoint**: `/mcp` (FastMCP default)

### Rationale
HTTP transport is required by FR-001 and enables network access for MCP clients. FastMCP 2.0+ provides native HTTP support with minimal configuration. Port 8000 is a common default for development servers.

### Implementation Pattern

**Server Setup (Python):**
```python
from fastmcp import FastMCP

mcp = FastMCP("Memento")

@mcp.tool()
def remember(content: str, confidence: float) -> dict:
    # Implementation
    pass

if __name__ == "__main__":
    mcp.run(transport="http", port=8000, host="0.0.0.0")
```

**Configuration Extension:**
Add to `src/utils/config.py`:
```python
# MCP Server configuration
mcp_host: str = Field(default="0.0.0.0", description="MCP server host")
mcp_port: int = Field(default=8000, description="MCP server port")
```

### Key Considerations
- HTTP transport serves multiple clients (unlike STDIO)
- Server runs at `http://localhost:8000/mcp` by default
- FastMCP handles request/response serialization automatically
- Must handle async context for database operations

### Alternatives Considered
- **STDIO transport**: Rejected because HTTP is explicitly required (FR-001)
- **SSE transport**: Rejected as unnecessary complexity for baseline implementation
- **Custom port**: Using 8000 as sensible default, but making it configurable

### References
- [Running Your Server - FastMCP](https://gofastmcp.com/deployment/running-server)
- [Building MCP Server with FastMCP](https://medium.com/@anil.goyal0057/building-and-exposing-mcp-servers-with-fastmcp-stdio-http-and-sse-ace0f1d996dd)
- [FastMCP Transport Guide](https://github.com/tnpaul/fastmcp-transport-guide)

---

## Decision 3: Neo4j Python Driver Operations

### Decision
Use Neo4j Python driver 5.28+ with session management pattern:
- **Connection**: Single driver instance (reuse connections)
- **Session Management**: Context manager pattern for transactions
- **Cypher Execution**: Explicit queries via `session.run()`
- **Parameter Binding**: Named parameters to prevent injection

### Rationale
The project already declares `neo4j>=5.28.0` as a dependency. The standard driver pattern uses a single driver instance with session-based transactions, following Neo4j best practices.

### Implementation Pattern

**Repository Initialization:**
```python
from neo4j import GraphDatabase

class Neo4jRepository:
    def __init__(self, uri: str, user: str, password: str):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()
```

**Store Memory Operation:**
```python
def create_memory(self, memory: Memory) -> Memory:
    with self._driver.session() as session:
        result = session.run(
            """
            CREATE (m:Memory {
                id: $id,
                content: $content,
                embedding: $embedding,
                created_at: datetime($created_at)
            })
            RETURN m
            """,
            id=memory.id,
            content=memory.content,
            embedding=memory.embedding,
            created_at=memory.created_at.isoformat()
        )
        return memory
```

**Ensure Vector Index:**
```python
def ensure_vector_index(self):
    with self._driver.session() as session:
        session.run(
            """
            CREATE VECTOR INDEX memory_embedding_index IF NOT EXISTS
            FOR (m:Memory)
            ON m.embedding
            OPTIONS { indexConfig: {
                `vector.dimensions`: 384,
                `vector.similarity_function`: 'cosine'
            }}
            """
        )
```

### Key Considerations
- Driver instance should be singleton (single instance per application)
- Sessions are short-lived (one per operation)
- Use context managers to ensure resource cleanup
- Named parameters prevent Cypher injection
- Driver is thread-safe; sessions are not

### Alternatives Considered
- **OGM (Object-Graph Mapping)**: Rejected as premature complexity (YAGNI)
- **Multiple driver instances**: Rejected due to connection pool overhead
- **Direct Cypher strings**: Rejected in favor of parameterized queries for safety

### References
- [Neo4j Python Driver 6.0 Documentation](https://neo4j.com/docs/api/python-driver/current/)
- [Build Applications with Neo4j and Python](https://neo4j.com/docs/python-manual/current/)
- [neo4j · PyPI](https://pypi.org/project/neo4j/)

---

## Decision 4: Configuration Management for Max Memory Length

### Decision
Extend existing `Config` class in `src/utils/config.py` with:
- **Field**: `max_memory_length` (default: 4000)
- **Type**: `int` with validation
- **Environment Variable**: `MEMENTO_MAX_MEMORY_LENGTH`

### Rationale
The project already uses Pydantic Settings for configuration with `MEMENTO_` prefix. Adding `max_memory_length` follows the established pattern and makes the limit configurable without code changes (FR-008).

### Implementation Pattern

**Config Extension:**
```python
class Config(BaseSettings):
    # ... existing fields ...

    # Memory validation configuration
    max_memory_length: int = Field(
        default=4000,
        ge=1,
        le=100000,
        description="Maximum allowed memory text length in characters"
    )
```

**Usage in Service:**
```python
def validate_memory_text(self, text: str):
    if len(text.strip()) == 0:
        raise ValueError("Memory text cannot be empty or whitespace-only")
    if len(text) > self._config.max_memory_length:
        raise ValueError(
            f"Memory text exceeds maximum length of {self._config.max_memory_length} characters"
        )
```

### Key Considerations
- Pydantic Field validation ensures value is positive and reasonable
- Environment variable override allows deployment-specific limits
- Default of 4000 matches clarified requirement
- Upper bound of 100000 prevents unreasonable configuration

### Alternatives Considered
- **Hardcoded constant**: Rejected because FR-008 requires configurability
- **Separate config file**: Rejected to maintain consistency with existing env-based config
- **No upper limit validation**: Rejected to prevent misconfiguration

---

## Decision 5: Memory Data Model

### Decision
Simplify the existing `Memory` dataclass in `src/models/memory.py` by removing supersession-related fields:
- **Keep**: id, content, embedding, confidence, created_at, updated_at, accessed_at
- **Remove**: source, supersedes, superseded_by
- **Confidence scale**: float, 0.0-1.0 (standard normalized scale)

### Rationale
The existing `Memory` model already has the core fields we need. Removing only the supersession fields (source, supersedes, superseded_by) follows YAGNI while avoiding code duplication. Keeping confidence, updated_at, and accessed_at provides valuable metadata without adding complexity. The 0-1 confidence scale is standard for ML/AI systems.

### Implementation Pattern

**Model Definition (simplified from original Memory):**
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Memory:
    """
    Represents a stored memory in the baseline RAG system.

    Simplified from original Memory model with supersession fields removed.

    Attributes:
        id: Unique UUID identifier (as string)
        content: The exact memory text from the user
        embedding: 384-dimensional vector embedding
        confidence: Confidence score (0-1 scale, higher = more reliable)
        created_at: Timestamp when memory was created
        updated_at: Timestamp of last modification
        accessed_at: Timestamp of last retrieval
    """
    id: str
    content: str
    embedding: list[float]
    confidence: float  # 0.0 to 1.0
    created_at: datetime
    updated_at: datetime
    accessed_at: datetime
```

### Key Considerations
- UUID stored as string for Neo4j compatibility
- Embedding as `list[float]` matches `IEmbeddingProvider` interface
- Field name is `content` to store the exact memory text from the user
- Confidence input required from MCP tool (0-1 scale, standard normalized range)
- No validation in dataclass; validation happens in service layer

### Alternatives Considered
- **Keep all Memory fields**: Rejected because source/supersedes/superseded_by are out of scope (YAGNI)
- **Remove confidence/timestamps**: Rejected because they provide valuable metadata without complexity
- **Pydantic model**: Rejected to maintain consistency with existing dataclass pattern

---

## Summary

All technical decisions leverage existing infrastructure:
- **Embedding**: Use existing `LocalEmbeddingProvider` with `all-MiniLM-L6-v2`
- **Configuration**: Extend existing Pydantic `Config` class
- **Architecture**: Follow existing layered pattern (MCP → Service → Repository → Provider)
- **Testing**: Use existing pytest setup

No new dependencies required beyond what's already in `pyproject.toml`.

## Sources

- [Neo4j Vector Indexes Documentation](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/)
- [Running Your Server - FastMCP](https://gofastmcp.com/deployment/running-server)
- [Building MCP Server with FastMCP](https://medium.com/@anil.goyal0057/building-and-exposing-mcp-servers-with-fastmcp-stdio-http-and-sse-ace0f1d996dd)
- [FastMCP Transport Guide](https://github.com/tnpaul/fastmcp-transport-guide)
- [Neo4j Python Driver 6.0 Documentation](https://neo4j.com/docs/api/python-driver/current/)
- [Build Applications with Neo4j and Python](https://neo4j.com/docs/python-manual/current/)
- [neo4j · PyPI](https://pypi.org/project/neo4j/)
