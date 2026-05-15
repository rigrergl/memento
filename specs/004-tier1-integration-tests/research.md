# Research: Tier-1 Integration Tests

**Branch**: `004-tier1-integration-tests` | **Phase**: 0 Output

## Decision 1: testcontainers[neo4j] as the container harness

**Decision**: Use `testcontainers[neo4j]` (main `testcontainers` package, version 4.14.2) for Neo4j container lifecycle.

**Rationale**: Official Neo4j testcontainers module; `Neo4jContainer.get_connection_url()` returns the mapped Bolt URI; `.start()/.stop()` pair works cleanly with pytest session-scoped yield fixtures; `neo4j:2026.03.1` is a valid Docker Hub tag (confirmed via API).

**Alternatives considered**: Manual `docker run` subprocess — rejected (fragile, no readiness polling). `testcontainers-neo4j` stub on PyPI — dead package (0.0.1rc1), do not use.

**Key API**:
```python
from testcontainers.neo4j import Neo4jContainer

container = Neo4jContainer(image="neo4j:2026.03.1")
container.start()
bolt_uri = container.get_connection_url()   # "bolt://<host>:<mapped_port>"
# default creds: username="neo4j", password="password"
container.stop()
```

---

## Decision 2: FastMCP in-memory `Client` for MCP tool invocation

**Decision**: Use `from fastmcp import Client` with `async with Client(mcp) as client:` for all tool calls. The `mcp` object is imported from `src.mcp.server`.

**Rationale**: Fully in-memory, no subprocess or network required. Opening the async context manager automatically triggers the server lifespan (`ensure_vector_index` runs on entry, driver closes on exit). `call_tool` returns a `CallToolResult`; `result.data` gives the typed Python value directly.

**Alternatives considered**: HTTP transport against a running server — rejected (requires subprocess management, out of scope for FR-005). `subprocess` transport — rejected (same).

**Key API** (fastmcp 3.x):
```python
result = await client.call_tool("remember", {"content": "...", "confidence": 0.9})
text = result.data          # preferred: typed Python string
# or: result.content[0].text  # fallback: always str via MCP TextContent
assert not result.is_error
```

---

## Decision 3: pytest-asyncio 1.x session loop with `asyncio_mode = "auto"`

**Decision**: Add `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "session"` to `[tool.pytest.ini_options]` in `pyproject.toml`. Use `@pytest_asyncio.fixture(scope="session", loop_scope="session")` for the session-scoped Client fixture.

**Rationale**: pytest-asyncio 1.x removed the `event_loop` fixture; session-scoped async fixtures require explicit `loop_scope="session"` or pytest-asyncio raises `ScopeMismatch`. `asyncio_mode = "auto"` eliminates per-test `@pytest.mark.asyncio` markers. Both `scope=` and `loop_scope=` must be set on session-scoped async fixtures.

**Alternatives considered**: `asyncio_mode = "strict"` — works but requires `@pytest.mark.asyncio` on every test; unnecessary verbosity. Function-scoped Client (re-entering lifespan per test) — rejected; spec requires session-scoped Client (FR-008).

---

## Decision 4: Env var injection pattern for Config override

**Decision**: Set `MEMENTO_NEO4J_URI`, `MEMENTO_NEO4J_USER`, `MEMENTO_NEO4J_PASSWORD` in `os.environ` inside the session-scoped `neo4j_container` fixture (before the `client` fixture opens the lifespan). Static embedding vars (`MEMENTO_EMBEDDING_PROVIDER`, `MEMENTO_EMBEDDING_MODEL`) set at conftest module level.

**Rationale**: `Config()` (pydantic-settings with `env_prefix="MEMENTO_"`) is instantiated inside the `lifespan` function, not at `src.mcp.server` import time. Env vars only need to be present when `async with Client(mcp)` is entered. Session-fixture ordering guarantees `neo4j_container` starts before `client` opens.

**Alternatives considered**: Monkeypatching `Config` — rejected; more fragile than env var injection. `.env` file patching — rejected; env vars are cleaner for test-only overrides.

---

## Decision 5: Actual MCP response strings (from source code)

The spec refers to "documented error strings" — the actual strings from `src/mcp/server.py` and `src/memory/service.py` are:

| Path | Trigger | Response String |
|------|---------|----------------|
| remember success | — | `"Memory stored with id: {uuid}"` |
| remember error | empty content | `"Memory text cannot be empty."` |
| remember error | content too long | `"Memory text exceeds maximum length of 4000 characters (got {n})."` |
| remember error | confidence out of range | `"Invalid confidence value {v}: must be between 0.0 and 1.0."` |
| recall success | results found | `'Found {n} result(s) for "{query}":\n1. (score: {s:.3f}) {content}...'` |
| recall no results | nothing stored | `'No memories found for "{query}".'` |
| recall error | empty query | `"Query cannot be empty."` |

---

## Decision 6: Actual Neo4j `Memory` node fields (from source code)

The spec says "10 expected fields." The actual 10 fields persisted by `Neo4jRepository.create_memory()` are:

`id`, `content`, `embedding`, `confidence`, `created_at`, `updated_at`, `accessed_at`, `source`, `supersedes`, `superseded_by`

The `embedding` field is a float vector (384 dimensions). The `supersedes`/`superseded_by` fields default to `None` (stored as `null` in Neo4j). Tests asserting graph state should check these 10 fields.

---

## Decision 7: Cleanup query scope

**Decision**: Use `MATCH (n:Memory) DETACH DELETE n` for per-test cleanup (label-filtered, not bare `MATCH (n)`).

**Rationale**: Scoping the delete to `Memory`-labeled nodes is safer and faster. Neo4j schema objects (vector index, uniqueness constraint) are not data nodes and are unaffected by either variant. Label-filtering prevents accidental deletion of any future non-Memory nodes.
