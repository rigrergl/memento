# Quickstart: Baseline RAG - Store Memory

**Feature**: Store memories with vector embeddings via MCP HTTP server
**Target Audience**: Developers implementing or testing this feature

## Prerequisites

- Python 3.10+
- Neo4j database (local or cloud instance with vector index support)
- Required environment variables configured

## Setup

### 1. Configure Environment

Create a `.env` file in the project root:

```bash
# Neo4j Configuration (REQUIRED)
MEMENTO_NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
MEMENTO_NEO4J_USER=neo4j
MEMENTO_NEO4J_PASSWORD=your-password-here

# Embedding Configuration (uses defaults if not specified)
MEMENTO_EMBEDDING_PROVIDER=local
MEMENTO_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MEMENTO_EMBEDDING_CACHE_DIR=.cache/models

# Memory Validation (optional, uses defaults)
MEMENTO_MAX_MEMORY_LENGTH=4000

# MCP Server (optional, uses defaults)
MEMENTO_MCP_HOST=0.0.0.0
MEMENTO_MCP_PORT=8000
```

### 2. Install Dependencies

```bash
uv sync
```

This installs all dependencies from `pyproject.toml`:
- `fastmcp>=2.11.0` - MCP server framework
- `neo4j>=5.28.0` - Neo4j Python driver
- `sentence-transformers>=5.1.0` - Embedding generation
- `pydantic>=2.11.0` - Configuration management
- `pydantic-settings>=2.11.0` - Environment variable loading

### 3. Start the MCP Server

```bash
uv run python -m src.mcp.server
```

Expected output:
```
MCP server running at http://0.0.0.0:8000/mcp
Registered tools: remember
```

The server is now ready to accept requests.

## Using the `remember` Tool

### Via HTTP Request

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "remember",
      "arguments": {
        "content": "My favorite color is blue",
        "confidence": 0.85
      }
    },
    "id": 1
  }'
```

### Expected Response

**Success:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "memory_id": "550e8400-e29b-41d4-a716-446655440000",
    "content": "My favorite color is blue",
    "confidence": 0.85,
    "created_at": "2025-12-24T10:30:00+00:00",
    "embedding_dimensions": 384
  },
  "id": 1
}
```

**Validation Error (empty text):**
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Memory text cannot be empty or whitespace-only"
  },
  "id": 1
}
```

**Validation Error (exceeds max length):**
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Memory text exceeds maximum length of 4000 characters",
    "data": {
      "length": 5000,
      "max_length": 4000
    }
  },
  "id": 1
}
```

**Validation Error (invalid confidence):**
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Confidence must be between 0.0 and 1.0",
    "data": {
      "confidence": 1.5
    }
  },
  "id": 1
}
```

## Verifying Data in Neo4j

### Connect to Neo4j Browser

Navigate to your Neo4j instance (e.g., https://browser.neo4j.io/) and run:

**Check if Memory nodes exist:**
```cypher
MATCH (m:Memory)
RETURN m.id, m.content, m.confidence, m.created_at
ORDER BY m.created_at DESC
LIMIT 10
```

**Verify vector index exists:**
```cypher
SHOW VECTOR INDEXES
YIELD name, state, populationPercent
WHERE name = 'memory_embedding_index'
```

Expected output:
```
name                      | state   | populationPercent
memory_embedding_index    | ONLINE  | 100.0
```

**Check embedding dimensions:**
```cypher
MATCH (m:Memory)
RETURN m.id, size(m.embedding) AS dimensions
LIMIT 5
```

Expected: All rows should show `dimensions: 384`

## Running Tests

### Run All Tests

```bash
uv run pytest
```

### Run Specific Test Suites

```bash
# Test Memory model
uv run pytest tests/test_models/test_memory.py

# Test MemoryService
uv run pytest tests/test_memory/test_service.py

# Test Neo4jRepository
uv run pytest tests/test_graph/test_neo4j.py

# Test MCP tool
uv run pytest tests/test_mcp/test_server.py
```

### Run with Coverage

```bash
uv run pytest --cov=src --cov-report=html
```

View coverage report at `htmlcov/index.html`

## Development Workflow (TDD)

Following the constitution's TDD principle:

### 1. Write a Failing Test

```python
# tests/test_memory/test_service.py
def test_store_memory_creates_memory():
    service = MemoryService(...)
    result = service.store_memory("My favorite color is blue", confidence=0.85)

    assert result.memory_id is not None
    assert result.content == "My favorite color is blue"
    assert result.confidence == 0.85
    # This test FAILS because store_memory doesn't exist yet
```

### 2. Run Tests (RED)

```bash
uv run pytest tests/test_memory/test_service.py::test_store_memory_creates_memory
```

Expected: `FAILED - AttributeError: 'MemoryService' object has no attribute 'store_memory'`

### 3. Implement Minimum Code (GREEN)

```python
# src/memory/service.py
class MemoryService:
    def store_memory(self, content: str, confidence: float) -> dict:
        # Minimum implementation to pass test
        now = datetime.now(timezone.utc)
        memory = Memory(
            id=str(uuid.uuid4()),
            content=content,
            embedding=self._embedder.generate_embedding(content),
            confidence=confidence,
            created_at=now,
            updated_at=now,
            accessed_at=now
        )
        self._repository.create_memory(memory)
        return {
            "memory_id": memory.id,
            "content": memory.content,
            "confidence": memory.confidence,
            "created_at": memory.created_at.isoformat(),
            "embedding_dimensions": 384
        }
```

### 4. Run Tests Again

```bash
uv run pytest tests/test_memory/test_service.py::test_store_memory_creates_memory
```

Expected: `PASSED`

### 5. Refactor (while keeping tests green)

Clean up code, extract methods, improve naming - all while keeping tests passing.

## Troubleshooting

### Issue: "Neo4j connection refused"

**Solution**: Verify Neo4j is running and URI/credentials are correct:
```bash
# Test connection with Neo4j Python driver
python -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('neo4j+s://your-uri', auth=('user', 'pass')); driver.verify_connectivity(); print('Connected!')"
```

### Issue: "Model download taking too long"

**Solution**: The first run downloads the `all-MiniLM-L6-v2` model (~80MB). Subsequent runs use the cached model in `.cache/models/`.

### Issue: "Vector index not found"

**Solution**: The index is created automatically on first `remember` call. Check index status:
```cypher
SHOW VECTOR INDEXES
```

If missing, manually create:
```cypher
CREATE VECTOR INDEX memory_embedding_index IF NOT EXISTS
FOR (m:Memory)
ON m.embedding
OPTIONS { indexConfig: {
  `vector.dimensions`: 384,
  `vector.similarity_function`: 'cosine'
}}
```

### Issue: "Tests fail with import errors"

**Solution**: Ensure you're running tests with `uv run pytest` (not bare `pytest`) to use the correct virtual environment.

## Next Steps

After implementing this baseline RAG feature:

1. **Verify all tests pass**: `uv run pytest`
2. **Check constitution compliance**: Review code against YAGNI, KISS, TDD principles
3. **Manual testing**: Use curl or Postman to test the HTTP endpoint
4. **Review Neo4j data**: Verify Memories are stored correctly with 384-dimensional embeddings

Future features (separate specs):
- **Search memories**: Semantic search using vector index
- **Graph relationships**: Subject-predicate-object triples
- **Memory supersession**: Mark old memories as outdated

## Reference

- **Spec**: [spec.md](./spec.md)
- **Plan**: [plan.md](./plan.md)
- **Data Model**: [data-model.md](./data-model.md)
- **Research**: [research.md](./research.md)
- **MCP Tool Contract**: [contracts/mcp-tool-remember.json](./contracts/mcp-tool-remember.json)
