# [Core] Implement Memory Service

**Epic:** Core Components (Phase 1)

## Description

Implement the core memory service layer that orchestrates embeddings and graph repository to provide high-level memory operations. This is the main business logic layer that MCP tools will interact with.

## Goal

Create a production-ready memory service that:
- Orchestrates embedding generation and database storage
- Provides semantic search across memories
- Handles memory supersession/updates
- Returns similar memories for conflict detection
- Implements all core memory operations

## Acceptance Criteria

- [ ] `src/memory/service.py` implements `GraphMemoryService` class
- [ ] Constructor accepts `embedding_provider`, `repository`, and optional `llm_provider`
- [ ] Implements `store_memory(user_id, content, confidence, source) -> dict` method
  - Generates embedding for content
  - Stores in repository
  - Returns stored memory + similar existing memories for conflict detection
- [ ] Implements `search_memories(user_id, query, limit) -> list[Memory]` method
  - Generates query embedding
  - Searches repository with vector similarity
  - Filters out superseded memories
  - Updates accessed_at timestamps
- [ ] Implements `get_recent_memories(user_id, limit) -> list[Memory]` method
- [ ] Implements `supersede_memory(old_memory_id, new_memory_id) -> None` method
  - Updates both old and new memory records
  - Creates SUPERSEDES relationship
- [ ] Proper error handling and validation
- [ ] Unit tests in `tests/test_memory/test_service.py` with >80% coverage
- [ ] Tests use mocks for embedding provider and repository
- [ ] Integration tests with real components
- [ ] Documentation/docstrings for all public methods

## Technical Details

**Key Operations:**

**store_memory:**
```python
async def store_memory(
    self,
    user_id: str,
    content: str,
    confidence: float = 1.0,
    source: str = 'extracted'
) -> dict:
    # 1. Generate embedding
    embedding = await self.embedding_provider.generate_embedding(content)

    # 2. Store in repository
    memory = await self.repository.create_memory(user_id, {
        'content': content,
        'embedding': embedding,
        'confidence': confidence,
        'source': source,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'accessed_at': datetime.now()
    })

    # 3. Find similar memories for conflict detection
    similar = await self.search_memories(user_id, content, limit=5)

    return {
        'stored': memory,
        'similar_memories': similar
    }
```

**search_memories:**
```python
async def search_memories(
    self,
    user_id: str,
    query: str,
    limit: int = 5
) -> list[Memory]:
    # 1. Generate query embedding
    query_embedding = await self.embedding_provider.generate_embedding(query)

    # 2. Vector search (repository handles superseded filtering)
    results = await self.repository.search_by_vector(
        user_id,
        query_embedding,
        limit * 2  # Get extra for filtering
    )

    # 3. Update access timestamps
    for memory in results[:limit]:
        await self.repository.update_memory(memory.id, {
            'accessed_at': datetime.now()
        })

    return results[:limit]
```

**Dependencies:**
- Requires `IEmbeddingProvider` from embeddings layer
- Requires `Neo4jRepository` from graph layer
- Requires `Memory` model from `src/models/`
- All dependencies injected via constructor (dependency injection pattern)

**Testing Strategy:**
- Unit tests: Mock embedding provider and repository
- Integration tests: Use real embedding provider + test Neo4j instance
- Test conflict detection by storing similar memories
- Test supersession chains

## Estimated Complexity

**Medium** - Orchestration logic with proper testing and error handling
