# Feature Specification: Tier-1 Integration Test Suite

**Feature Branch**: `004-tier1-integration-tests`  
**Created**: 2026-05-12  
**Status**: Draft  

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Agent runs full test suite and gets a pass/fail signal (Priority: P1)

An AI coding agent (Claude Code in YOLO mode, Jules, Cloud Code) has just edited `MemoryService`, `Neo4jRepository`, or an MCP tool handler. The agent runs `uv run pytest` and receives a deterministic green or red result that covers both unit tests and the end-to-end integration path against a real Neo4j.

**Why this priority**: This is the primary goal of the feature. Without a reliable full-suite signal, agents cannot safely hand off changes. All other stories depend on this infrastructure existing.

**Independent Test**: Run `uv run pytest` in a clean checkout with Docker available — the suite completes with the integration tests exercising a live Neo4j container, and exits 0 on a correct implementation.

**Acceptance Scenarios**:

1. **Given** Docker is running and the codebase is unchanged, **When** `uv run pytest` is executed, **Then** all unit tests and all integration tests pass, the Neo4j testcontainer starts automatically, and the exit code is 0.
2. **Given** Docker is running, **When** a breaking change is introduced to `MemoryService.remember()`, **Then** at least one integration test fails with a descriptive error, and the exit code is non-zero.
3. **Given** Docker is NOT running, **When** `uv run pytest` is executed, **Then** the integration tests fail loudly (not skip) with a clear error indicating Docker is required.

---

### User Story 2 — `remember` tool round-trip validates both MCP response and graph state (Priority: P1)

An integration test calls the `remember` MCP tool through the FastMCP in-memory client against a real Neo4j. The test asserts the response string matches the documented contract AND queries Neo4j directly to confirm the node was persisted with all expected fields.

**Why this priority**: Correctness at both the protocol layer and the storage layer must be verified. A test that only checks the response string can miss Cypher bugs; a test that only checks the graph can miss serialization bugs.

**Independent Test**: Can be run in isolation with `uv run pytest tests/integration/test_remember.py` and delivers a meaningful signal about the remember path without running recall tests.

**Acceptance Scenarios**:

1. **Given** a clean Neo4j database, **When** `remember` is called with valid content, metadata, and confidence, **Then** the MCP response string matches the documented "Memory stored successfully" contract, AND a `Memory` node exists in Neo4j with all 10 expected fields populated (id, content, metadata, confidence, created_at, updated_at, access_count, last_accessed, source, memory_type), AND a vector embedding is stored on the node.
2. **Given** a clean Neo4j database, **When** `remember` is called with empty content, **Then** the MCP response is the documented error string, AND no `Memory` node is created in Neo4j.
3. **Given** a clean Neo4j database, **When** `remember` is called with content exceeding the maximum allowed length, **Then** the MCP response is the documented error string for over-length content, AND no `Memory` node is created.
4. **Given** a clean Neo4j database, **When** `remember` is called with a confidence value outside the valid range (e.g., 1.5 or -0.1), **Then** the MCP response is the documented error string for invalid confidence, AND no `Memory` node is created.

---

### User Story 3 — `recall` tool round-trip validates response, result count, and limit behavior (Priority: P1)

An integration test seeds Neo4j with known memories, then calls the `recall` MCP tool through the FastMCP in-memory client. The test asserts the response matches the documented contract, relevant memories are returned, and the `limit` parameter is honored.

**Why this priority**: Recall is the primary read path. Correctness here is as important as correctness of the write path.

**Independent Test**: Can be run in isolation with `uv run pytest tests/integration/test_recall.py` after the database has been seeded in conftest.

**Acceptance Scenarios**:

1. **Given** one or more memories have been stored, **When** `recall` is called with a semantically matching query, **Then** the MCP response contains at least one result whose content is relevant to the query.
2. **Given** no memories have been stored (clean database), **When** `recall` is called with any query, **Then** the MCP response matches the documented "no memories found" contract string.
3. **Given** multiple memories exist, **When** `recall` is called with `limit=2`, **Then** the response contains at most 2 results.
4. **Given** an empty query string is passed to `recall`, **Then** the MCP response is the documented error string for empty query, and no results are returned.

---

### User Story 4 — Lifespan hook runs against real Neo4j and creates required schema artifacts (Priority: P2)

The FastMCP lifespan hook (`ensure_vector_index`) is exercised against the real testcontainers Neo4j. The test confirms the vector index and uniqueness constraint are created on startup and persist across the test session.

**Why this priority**: The lifespan hook is infrastructure-critical. If it breaks, all write and search operations fail silently or with cryptic errors.

**Independent Test**: Inspectable as part of the session-scoped conftest setup — querying Neo4j's index and constraint metadata after lifespan runs.

**Acceptance Scenarios**:

1. **Given** a fresh Neo4j container with no schema, **When** the MCP server lifespan runs, **Then** a vector index on `Memory` nodes exists in Neo4j, AND a uniqueness constraint on `Memory.id` exists.
2. **Given** the lifespan has already run, **When** tests run and call `remember` and `recall`, **Then** no "index not found" or "constraint violation" errors occur.

---

### Edge Cases

- What happens when the Neo4j container takes longer than expected to become ready? (testcontainers handles readiness polling; startup must not require manual sleep)
- How does the test suite behave when the sentence-transformers model is not yet cached? (first-run download is acceptable; test must not time out unreasonably)
- What if a test fails mid-suite and leaves dirty graph state? (each test cleans the database with `MATCH (n) DETACH DELETE n` before running, so test ordering does not matter)
- What if `ensure_vector_index` is called on a database that already has the index? (must be idempotent — no error, no duplicate index created)

## Clarifications

### Session 2026-05-14

- Q: How does the testcontainer's Neo4j URI reach the `mcp` object's internal repository? → A: Env var override — conftest sets `NEO4J_URI` and credentials in `os.environ` before importing `src.mcp.server`; server.py reads all Neo4j config from env vars via pydantic-settings.
- Q: How is the FastMCP lifespan hook triggered in the in-memory test client context? → A: Opening a session-scoped `async with Client(mcp)` fixture automatically triggers the lifespan hook (`ensure_vector_index`) on context entry.
- Q: Should integration tests be documented as incompatible with `pytest-xdist` parallel execution? → A: Yes — AGENTS.md must explicitly state that integration tests run sequentially; xdist causes race conditions on the shared Neo4j per-test cleanup.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The test suite MUST include a `tests/integration/` directory with its own `conftest.py` that is not imported by or dependent on `tests/test_mcp/conftest.py`.
- **FR-002**: `conftest.py` MUST start a single Neo4j testcontainer scoped to the pytest session using `testcontainers[neo4j]` with the image `neo4j:2026.03.1`.
- **FR-003**: `conftest.py` MUST clean the database between tests using `MATCH (n) DETACH DELETE n`, while preserving session-scoped schema artifacts (vector index, uniqueness constraint).
- **FR-004**: `conftest.py` MUST set the testcontainer's Neo4j URI and credentials as environment variables in `os.environ` before `src.mcp.server` is imported, so that the `mcp` object's internal `Neo4jRepository` connects to the testcontainer via pydantic-settings config resolution. A real `LocalEmbeddingProvider` using the production sentence-transformers model MUST be used.
- **FR-005**: Integration tests MUST exercise MCP tools via the FastMCP in-memory `Client(mcp)` pattern against the real `mcp` object from `src/mcp/server.py` — no subprocess, no HTTP transport.
- **FR-006**: The `remember` integration tests MUST assert both the MCP response string (protocol layer) and the Neo4j node state (storage layer) for success and error paths.
- **FR-007**: The `recall` integration tests MUST assert the MCP response string for success paths, the no-results path, the limit-honored path, and the empty-query error path.
- **FR-008**: The lifespan hook MUST be exercised via a session-scoped `async with Client(mcp)` fixture in `conftest.py`; FastMCP automatically runs `ensure_vector_index` on context entry, creating the vector index and uniqueness constraint against the real Neo4j.
- **FR-009**: `pyproject.toml`'s `[dependency-groups] dev` MUST include `testcontainers[neo4j]`.
- **FR-010**: No pytest marker, skip logic, or Docker-availability detection MUST be added — if Docker is unavailable, tests fail loudly.
- **FR-011**: AGENTS.md MUST be updated with a `## Prerequisites` section (D1), a restructured `## Testing` section (D2), a pointer to the constitutional principles in `## Development Philosophy` (D3), and an explicit note that integration tests are incompatible with `pytest-xdist` and must run sequentially (D4).

### Key Entities

- **Memory node**: The Neo4j node type persisted by `remember`. Has 10 fields: `id`, `content`, `metadata`, `confidence`, `created_at`, `updated_at`, `access_count`, `last_accessed`, `source`, `memory_type`. Has an associated vector embedding stored on the node.
- **MCP tool response**: The string value returned by the FastMCP `Client` after calling `remember` or `recall`. Documented in `Documentation/mcp-tool-specification.md`.
- **Vector index**: A Neo4j vector index on `Memory` nodes, created by `ensure_vector_index` during the lifespan hook.
- **Uniqueness constraint**: A Neo4j constraint on `Memory.id`, created by `ensure_vector_index` during the lifespan hook.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer (human or AI agent) can run `uv run pytest` with Docker available and receive a complete pass/fail result covering both unit and integration tests within a single command, with no additional setup steps beyond having Docker running.
- **SC-002**: A failing change to the `remember` or `recall` code path causes at least one integration test to fail, providing a specific error message that identifies which assertion failed (protocol response vs. graph state).
- **SC-003**: The integration test suite covers 100% of the tool-level success and documented error paths for `remember` and `recall` as specified in the MCP tool contract.
- **SC-004**: The session-scoped Neo4j container starts once and is reused for the entire test session; test isolation is achieved through per-test data cleanup, not container restarts.
- **SC-005**: After this feature ships, AGENTS.md alone is sufficient for an agent to understand: (a) Docker is required, (b) `uv run pytest` runs both unit and integration tests, (c) the full suite must be green before declaring done, and (d) where to find the full constitutional principles.

## Assumptions

- Docker is available in all environments where Memento is actively developed. This spec promotes that assumption from de-facto to de-jure.
- The sentence-transformers model used by `LocalEmbeddingProvider` is cacheable and does not require network access after the first download.
- The FastMCP in-memory `Client(mcp)` pattern supports async context manager usage and exposes `call_tool()` for invoking registered tools, consistent with the FastMCP test documentation at https://gofastmcp.com/development/tests.
- The MCP tool response strings for error paths are stable and documented in `Documentation/mcp-tool-specification.md`. If the spec discovers undocumented error strings during implementation, they are recorded there.
- `ensure_vector_index` is idempotent — calling it on a database that already has the index and constraint produces no error and no duplicate schema object.
- server.py reads all Neo4j connection configuration (URI, username, password) from environment variables via pydantic-settings; no hardcoded defaults conflict with the conftest injection mechanism.
- Integration tests are sequential-only. Running with `pytest-xdist` will cause race conditions on the shared Neo4j container's per-test cleanup (`MATCH (n) DETACH DELETE n`) and is not supported.

## Non-Goals

- HTTP/stdio transport boundary testing (Tier 2 — separate spec).
- LLM-driven tool-selection or tool-description ergonomics testing (Tier 3 — separate spec).
- Modifying or replacing any existing unit tests in `tests/test_mcp/` or `tests/test_graph/`.
- CI pipeline integration — local always-on is the gate this spec ships.
- Performance benchmarks or latency targets.
- Adding pytest markers, skip logic, or Docker-availability detection/graceful degradation.
