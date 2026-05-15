# Implementation Plan: Tier-1 Integration Test Suite

**Branch**: `004-tier1-integration-tests` | **Date**: 2026-05-14 | **Spec**: `specs/004-tier1-integration-tests/spec.md`
**Input**: Feature specification from `/specs/004-tier1-integration-tests/spec.md`

## Summary

Add a `tests/integration/` directory with a session-scoped Neo4j testcontainer, a FastMCP in-memory `Client` fixture, and test files covering the `remember` and `recall` MCP tools end-to-end. Tests assert both the MCP response string (protocol layer) and graph state (storage layer) against a real Neo4j instance. Also updates AGENTS.md with prerequisites, testing instructions, and xdist incompatibility note.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: FastMCP 3.x, testcontainers[neo4j] 4.14.2, pytest-asyncio 1.2+, neo4j-python-driver 5.28+
**Storage**: Neo4j testcontainer (image `neo4j:2026.03.1`) — session-scoped, started by conftest
**Testing**: pytest 8.4+, pytest-asyncio 1.2+, testcontainers[neo4j], pytest-cov 7.0+
**Target Platform**: Linux (Docker required; no Docker-detection fallback per FR-010)
**Project Type**: Single Python project
**Performance Goals**: N/A — test suite addition only
**Constraints**: Sequential-only (no pytest-xdist); Docker must be running; no skip/marker logic
**Scale/Scope**: 3 new test files (~35 test functions), 1 new conftest, 2 pyproject.toml changes, 1 AGENTS.md update

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. YAGNI | ✅ PASS | No speculative abstractions — only what the spec requires |
| II. KISS | ✅ PASS | Simple pytest fixtures; no helper classes or base classes |
| III. Design Patterns | ✅ PASS | Follows pytest conftest patterns throughout |
| IV. Layered Architecture | ✅ PASS | Tests exercise via FastMCP Client → all layers naturally |
| V. Mandatory Testing | ✅ PASS | This feature IS the tests; existing suite remains green |
| VI. TDD Gate | ✅ PASS | Tests are written first (they are the implementation) |

**Post-design re-check**: No violations introduced. No new application patterns, no new abstractions, no cross-layer shortcuts.

## Project Structure

### Documentation (this feature)

```text
specs/004-tier1-integration-tests/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── mcp-tool-responses.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
tests/
├── integration/          # NEW — entire directory
│   ├── __init__.py
│   ├── conftest.py       # session Neo4j container + FastMCP Client + cleanup
│   ├── test_remember.py  # FR-006: protocol + graph state assertions
│   ├── test_recall.py    # FR-007: response string + limit + error assertions
│   └── test_lifespan.py  # FR-008: vector index + uniqueness constraint

pyproject.toml            # add testcontainers[neo4j] to dev group; add asyncio_mode

AGENTS.md                 # FR-011: Prerequisites, Testing, xdist note, constitution pointer
```

**Structure Decision**: Single-project layout. The `tests/integration/` directory is a new peer alongside existing `tests/test_mcp/`, `tests/test_graph/`, etc. It has its own conftest.py independent of `tests/test_mcp/conftest.py` per FR-001.

## Implementation Notes

### conftest.py design

The session-scoped fixtures chain in this dependency order:

```
neo4j_container (session, sync)
  └── sets MEMENTO_NEO4J_* env vars
  └── neo4j_driver (session, sync) — for graph-state assertions
  └── client (session, async) — FastMCP in-memory client; triggers lifespan
        └── lifespan runs: Config() reads env vars → connects to testcontainer
              └── ensure_vector_index() → creates schema artifacts

clean_db (function, autouse=True)
  └── uses neo4j_driver
  └── runs MATCH (n:Memory) DETACH DELETE n after each test
```

**Why `neo4j_driver` is separate**: Tests in `test_remember.py` and `test_lifespan.py` need to query Neo4j directly (graph-state assertions). The driver must be session-scoped to avoid creating a new connection per test.

**Env var injection**: `MEMENTO_EMBEDDING_PROVIDER` and `MEMENTO_EMBEDDING_MODEL` are set at conftest module level (static). `MEMENTO_NEO4J_URI/USER/PASSWORD` are set inside `neo4j_container` fixture (dynamic — known only after container starts). `os.environ[...] = ...` (not `setdefault`) overrides any values set by unit-test conftest during the same session.

**Import ordering**: `from src.mcp.server import mcp` at conftest top level is safe — `Config()` is not instantiated at import time; it runs inside the `lifespan` function when `async with Client(mcp)` is entered.

### pytest-asyncio configuration

Add to `[tool.pytest.ini_options]` in `pyproject.toml`:
```toml
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
```

Session-scoped async fixtures must use `@pytest_asyncio.fixture(scope="session", loop_scope="session")`. Both `scope` and `loop_scope` must be specified — pytest-asyncio 1.x raises `ScopeMismatch` if they differ.

### testcontainers[neo4j] dependency

Add to `[dependency-groups] dev` in `pyproject.toml`:
```toml
"testcontainers[neo4j]>=4.8.0",
```

(4.8.0 is the minimum that ships the `Neo4jContainer` with `get_connection_url()`; 4.14.2 is current stable.)

### MCP tool response assertions

Use `result.data` (FastMCP 3.x `CallToolResult.data` attribute) for the string value. See `contracts/mcp-tool-responses.md` for exact strings.

- `remember` success: `assert result.data.startswith("Memory stored with id: ")`
- `remember` empty content: `assert result.data == "Memory text cannot be empty."`
- `recall` no results: `assert result.data == f'No memories found for "{query}".'`
- `recall` empty query: `assert result.data == "Query cannot be empty."`

### Graph-state assertions (test_remember.py)

After a successful `remember` call, query Neo4j directly:
```python
with neo4j_driver.session() as session:
    record = session.run("MATCH (m:Memory) RETURN m").single()
node = record["m"]
assert node["id"] is not None
assert node["content"] == expected_content
assert node["embedding"] is not None
assert len(node["embedding"]) == 384
assert node["confidence"] == expected_confidence
assert node["created_at"] is not None
assert node["updated_at"] is not None
assert node["accessed_at"] is not None
assert node["source"] == "user_requested"
# supersedes and superseded_by are None (null) by default
```

### Lifespan assertions (test_lifespan.py)

Query Neo4j schema metadata after the session-scoped `client` fixture has entered (lifespan has run):
```python
# Vector index check
records = session.run("SHOW INDEXES WHERE type = 'VECTOR' AND name = 'memory_embedding_index'")
assert records.single() is not None

# Constraint check
records = session.run("SHOW CONSTRAINTS WHERE name = 'memory_id_unique'")
assert records.single() is not None
```

## Complexity Tracking

No constitution violations. No complexity justification needed.
