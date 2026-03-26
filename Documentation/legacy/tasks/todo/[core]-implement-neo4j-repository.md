# [Core] Implement Neo4j Repository

**Epic:** Core Components (Phase 1)

## Description

Implement the Neo4j repository layer that handles all database operations for storing and retrieving memories. This will use Neo4j's graph structure and vector index capabilities for efficient semantic search.

## Goal

Create a production-ready Neo4j repository that:
- Connects to Neo4j Aura (cloud)
- Creates and manages vector indexes
- Implements CRUD operations for memories
- Handles user isolation for multi-tenancy
- Provides vector similarity search

## Acceptance Criteria

- [ ] `src/graph/neo4j.py` implements `Neo4jRepository` class
- [ ] Inherits from repository interface in `src/graph/base.py`
- [ ] Implements connection management with proper resource cleanup
- [ ] Creates vector index on first run (if not exists)
- [ ] Implements `create_memory(user_id, memory_data) -> Memory` method
- [ ] Implements `search_by_vector(user_id, embedding, limit) -> list[Memory]` method
- [ ] Implements `get_recent_memories(user_id, limit) -> list[Memory]` method
- [ ] Implements `update_memory(memory_id, updates) -> Memory` method for supersession
- [ ] Implements `create_user_if_not_exists(user_id) -> User` method
- [ ] Filters out superseded memories in search results
- [ ] Unit tests in `tests/test_graph/test_neo4j.py` with >80% coverage
- [ ] Integration tests against real Neo4j instance
- [ ] Error handling for connection failures

## Technical Details

**Neo4j Schema:**
```cypher
// Nodes
(:User {id: string, created_at: datetime})
(:Memory {
  id: string,
  content: string,
  embedding: list[float],
  confidence: float,
  source: string,
  supersedes: string?,
  superseded_by: string?,
  created_at: datetime,
  updated_at: datetime,
  accessed_at: datetime
})

// Relationships
(:User)-[:HAS_MEMORY]->(:Memory)
(:Memory)-[:SUPERSEDES]->(:Memory)

// Vector Index
CREATE VECTOR INDEX memory_embeddings FOR (m:Memory) ON m.embedding
OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}
```

**Key Implementation Points:**
- Use connection pooling via neo4j driver
- Use parameterized queries to prevent injection
- Handle vector index creation idempotently
- Filter superseded memories: `WHERE m.superseded_by IS NULL`
- Update accessed_at timestamp on retrieval
- Proper error handling and connection cleanup

**Configuration:**
- Read from environment: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Use `src/utils/config.py` for configuration management

**Dependencies:**
- `neo4j>=5.0.0`
- `python-dotenv>=1.0.0`
- Must define repository interface in `src/graph/base.py` first
- Requires `Memory` and `User` models from `src/models/`

## Estimated Complexity

**Large** - Complex database operations, vector indexing, and multi-tenancy considerations
