# Handoff: Baseline RAG (001-baseline-rag)

**Branch**: `001-baseline-rag`
**Status**: Implementation complete, all tests passing (64/64), 96% coverage
**Date**: 2026-03-07

---

## What Was Built

Two MCP tools exposed over HTTP via FastMCP, forming a complete read/write memory loop:

| Tool | Description | Key params |
|------|-------------|------------|
| `remember` | Embeds text and stores it as a Memory node in Neo4j | `content: str`, `confidence: float` |
| `recall` | Embeds a query and returns semantically similar memories | `query: str`, `limit: int = 10` |

### Files Created / Modified

```
src/
├── utils/config.py              MODIFIED — added max_memory_length, mcp_host, mcp_port fields
├── models/memory.py             MODIFIED — source field now defaults to "user_requested"
├── graph/
│   ├── base.py                  CREATED  — IGraphRepository interface (4 methods)
│   └── neo4j.py                 CREATED  — Neo4jRepository implementation
├── memory/service.py            CREATED  — MemoryService (store_memory, search_memory)
└── mcp/server.py                CREATED  — FastMCP server with remember + recall tools

tests/
├── test_models/
│   ├── __init__.py              CREATED
│   └── test_memory.py           CREATED  — 4 tests
├── test_graph/
│   └── test_neo4j.py            CREATED  — 10 tests (US1 + US2)
├── test_memory/
│   └── test_service.py          CREATED  — 16 tests (US1 + US2)
└── test_mcp/
    ├── __init__.py              CREATED
    ├── conftest.py              CREATED  — patches Neo4j + SentenceTransformer for import
    └── test_server.py           CREATED  — 17 tests (US1 + US2)

.env.example                     MODIFIED — added MEMENTO_MAX_MEMORY_LENGTH, MEMENTO_MCP_HOST, MEMENTO_MCP_PORT
README.md                        MODIFIED — added Quick Start section
```

---

## Architecture

Follows the layered pattern from `CLAUDE.md`:

```
MCP Server (src/mcp/server.py)
    └── MemoryService (src/memory/service.py)
            ├── IEmbeddingProvider (src/embeddings/base.py)  [existing]
            └── IGraphRepository (src/graph/base.py)
                    └── Neo4jRepository (src/graph/neo4j.py)
```

- **No dependencies flow upward** — lower layers know nothing about higher ones
- **Service orchestrates** — validation, UUID generation, timestamps, embedding calls
- **Repository handles Neo4j** — pure Cypher, no business logic
- **MCP layer is thin** — calls service, formats plain-text response, catches all exceptions

### Key implementation details

**`remember` flow:**
1. Validate content (non-empty, non-whitespace, ≤ `max_memory_length`)
2. Validate confidence (0.0–1.0)
3. Generate 384-dim embedding via `LocalEmbeddingProvider` (`all-MiniLM-L6-v2`)
4. Create `Memory` dataclass with `uuid.uuid4()` id and `datetime.now(timezone.utc)` timestamps
5. `repository.create_memory(memory)` — single Cypher `CREATE (:Memory {...})`
6. Return `"Memory stored with id: <uuid>"`

**`recall` flow:**
1. Validate query (non-empty, non-whitespace)
2. Validate limit (≥ 1)
3. Generate 384-dim embedding of the query
4. `repository.search_memories(embedding, limit)` — `CALL db.index.vector.queryNodes(...)`
5. Return numbered plain-text list with scores, or `"No memories found for ..."`

**Error handling:** Both tools catch `ValueError` → return `str(e)`; all other exceptions → return generic "Failed to ..." string. Exceptions never propagate to the MCP client.

**Vector index:** Created on server startup via `repository.ensure_vector_index()` in the `__main__` block. Uses `IF NOT EXISTS` — safe to call repeatedly. 384 dimensions, cosine similarity (hardcoded — see TD-002 in `Documentation/known-tech-debt.md`).

---

## How to Run

### 1. Create `.env`

```bash
cp .env.example .env
```

Required fields (no defaults):
```
MEMENTO_NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
MEMENTO_NEO4J_USER=neo4j
MEMENTO_NEO4J_PASSWORD=your-password-here
```

Optional (defaults shown):
```
MEMENTO_EMBEDDING_PROVIDER=local
MEMENTO_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MEMENTO_EMBEDDING_CACHE_DIR=.cache/models
MEMENTO_MAX_MEMORY_LENGTH=4000
MEMENTO_MCP_HOST=0.0.0.0
MEMENTO_MCP_PORT=8000
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Start the server

```bash
uv run python -m src.mcp.server
```

**First run note:** Downloads `all-MiniLM-L6-v2` (~80MB) to `.cache/models/`. Takes 1–2 minutes. Subsequent runs are instant.

On startup:
- Loads the embedding model
- Connects to Neo4j
- Creates the vector index and uniqueness constraint (idempotent)
- Starts HTTP server at `http://0.0.0.0:8000/mcp`

---

## How to Test with MCP Inspector

### Dev container workflow (recommended)

1. Start the server inside the dev container (see above)
2. Port 8000 is declared in `devcontainer.json` under `forwardPorts` — PyCharm (and VS Code) forward it to your host automatically
3. On your **host machine**, run:

```bash
npx @modelcontextprotocol/inspector
```

4. In the Inspector UI, connect to: `http://localhost:8000/mcp`

### Testing `remember`

```json
{
  "content": "My favorite color is blue",
  "confidence": 0.85
}
```

Expected response: `"Memory stored with id: <uuid>"`

### Testing `recall`

```json
{
  "query": "color preferences",
  "limit": 5
}
```

Expected response:
```
Found 1 result(s) for "color preferences":
1. (score: 0.954) My favorite color is blue
```

### Verifying data in Neo4j

In Neo4j Browser or Aura console:

```cypher
-- Check stored memories
MATCH (m:Memory)
RETURN m.id, m.content, m.confidence, m.created_at
ORDER BY m.created_at DESC
LIMIT 10

-- Verify vector index
SHOW VECTOR INDEXES
YIELD name, state, populationPercent
WHERE name = 'memory_embedding_index'

-- Check embedding dimensions
MATCH (m:Memory)
RETURN m.id, size(m.embedding) AS dimensions
LIMIT 5
```

---

## How to Run Tests

```bash
uv run pytest                                         # all 64 tests
uv run pytest --cov=src --cov-report=term-missing     # with coverage (currently 96%)
uv run pytest tests/test_graph/                       # repository layer only
uv run pytest tests/test_memory/                      # service layer only
uv run pytest tests/test_mcp/                         # MCP tool layer only
```

**All tests use mocks** — no real Neo4j connection or embedding model needed.

### Test structure note for future Claude instances

`tests/test_mcp/conftest.py` contains a `package`-scoped autouse fixture that:
- Sets required env vars (`MEMENTO_*`) so `Config()` can be instantiated
- Patches `SentenceTransformer` so the embedding model isn't loaded
- Patches `GraphDatabase` so no real Neo4j connection is made

This lets `src/mcp/server.py` (which runs module-level setup code on import) be imported in tests without real services. The scope is `package` (not `session`) to avoid leaking the patch into `tests/test_utils/` tests that exercise the real `LocalEmbeddingProvider`.

FastMCP wraps `@mcp.tool()` functions as `FunctionTool` objects — call the underlying function via `.fn(content=..., confidence=...)`, not directly.

---

## Known Issues / Caveats

### Neo4j version requirement
`recall` uses `CALL db.index.vector.queryNodes(...)` — requires **Neo4j 5.11+**. Neo4j Aura Free supports this. If you see "procedure not found", the instance is too old.

### `ensure_vector_index` only runs on `__main__`
The vector index is created in the `if __name__ == "__main__":` block. If you import `src.mcp.server` without running it as `__main__` (e.g., mounting it into another server), you'd need to call `repository.ensure_vector_index()` explicitly before the first `recall`.

### Tech debt TD-002 (vector similarity metric)
The cosine similarity metric is hardcoded at index creation time. Changing it requires dropping and recreating the index (and re-embedding all memories). See `Documentation/known-tech-debt.md`.

### Tech debt TD-001 (error detail logging)
Non-validation exceptions (embedding failures, Neo4j errors) return a generic string to the MCP client. Internal details are not logged anywhere yet. See `Documentation/known-tech-debt.md`.

---

## What's Next

Potential next specs (not started):
- **Memory supersession** — mark old memories as outdated when new ones contradict them
- **Entity graph extraction** — extract subject-predicate-object triples from stored memories
- **`forget` tool** — delete memories by ID
- **`update` tool** — modify existing memory content

To pick up where this left off, the next spec would build on:
- `IGraphRepository` — add new methods to the interface and `Neo4jRepository`
- `MemoryService` — add new operations
- `src/mcp/server.py` — register new tools following the same pattern

---

## Spec Artifacts

All spec documents for this feature live in `specs/001-baseline-rag/`:

| File | Purpose |
|------|---------|
| `spec.md` | User-facing requirements (non-technical) |
| `plan.md` | Technical design, file structure, tech stack |
| `data-model.md` | Memory entity, Neo4j schema, Config extension |
| `research.md` | Technical decisions and constraints |
| `contracts/remember-tool.md` | remember tool input/output/error contract |
| `contracts/recall-tool.md` | recall tool input/output/error contract |
| `quickstart.md` | Setup and usage guide |
| `tasks.md` | Full task breakdown (all 90 tasks marked complete) |
| `checklists/requirements.md` | Spec quality checklist (16/16 passed) |
