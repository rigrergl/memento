# Tasks: Tier-1 Integration Test Suite

**Input**: Design documents from `/specs/004-tier1-integration-tests/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/mcp-tool-responses.md ✅, quickstart.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Wire up dependencies and directory scaffolding so all test phases have what they need.

- [X] T001 Add `"testcontainers[neo4j]>=4.8.0"` to `[dependency-groups].dev` in `pyproject.toml`
- [X] T002 Add `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "session"` under `[tool.pytest.ini_options]` in `pyproject.toml`
- [X] T003 [P] Create empty `tests/integration/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement `tests/integration/conftest.py` with all session and function fixtures. Every test phase depends on this being complete before any test file is written.

**⚠️ CRITICAL**: No test file work can begin until this phase is complete.

- [X] T004 Create `tests/integration/conftest.py` with module-level static env vars (`MEMENTO_EMBEDDING_PROVIDER=local`, `MEMENTO_EMBEDDING_MODEL=all-MiniLM-L6-v2`) and the `neo4j_container` session fixture: starts `neo4j:2026.03.1` via `Neo4jContainer`, sets `MEMENTO_NEO4J_URI`, `MEMENTO_NEO4J_USER`, `MEMENTO_NEO4J_PASSWORD` in `os.environ`, yields, then calls `container.stop()`
- [X] T005 Add `neo4j_driver` session fixture to `tests/integration/conftest.py`: creates a `GraphDatabase.driver(bolt_uri, auth=(user, password))` using the env vars set by `neo4j_container`, yields the driver, closes on teardown — this fixture is used by tests that need to query Neo4j directly for graph-state assertions
- [X] T006 Add async `client` session fixture to `tests/integration/conftest.py` using `@pytest_asyncio.fixture(scope="session", loop_scope="session")`: imports `mcp` from `src.mcp.server`, opens `async with Client(mcp) as client`, yields `client` — this triggers the lifespan hook (`ensure_vector_index`) on entry
- [X] T007 Add `clean_db` function-scoped autouse fixture to `tests/integration/conftest.py`: after each test runs `MATCH (n:Memory) DETACH DELETE n` via `neo4j_driver` to remove data nodes while preserving schema artifacts (vector index, uniqueness constraint)

**Checkpoint**: `conftest.py` is complete — all fixtures are defined and all test files can now be implemented.

---

## Phase 3: User Story 2 — `remember` Round-Trip Tests (Priority: P1) 🎯 MVP

**Goal**: Verify the `remember` MCP tool at both the protocol layer (response string) and the storage layer (Neo4j graph state) for success and all documented error paths.

**Independent Test**: `uv run pytest tests/integration/test_remember.py`

- [X] T008 [US2] Create `tests/integration/test_remember.py` with `test_remember_success()`: calls `await client.call_tool("remember", {"content": "...", "confidence": 0.9})`, asserts `result.data.startswith("Memory stored with id: ")`, then uses `neo4j_driver` to `MATCH (m:Memory) RETURN m` and asserts all 10 fields: `id` (not None), `content` (matches input), `embedding` (not None, `len == 384`), `confidence` (matches input), `created_at`, `updated_at`, `accessed_at` (all not None), `source == "user_requested"`, `supersedes` (None), `superseded_by` (None)
- [X] T009 [US2] Add three validation-error tests to `tests/integration/test_remember.py`: `test_remember_empty_content()` — calls `remember` with `content=""`, asserts `result.data == "Memory text cannot be empty."` and `MATCH (n:Memory) RETURN n` returns no records; `test_remember_content_too_long()` — calls `remember` with a 4001-character string, asserts response matches `"Memory text exceeds maximum length of 4000 characters (got 4001)."` and no node created; `test_remember_invalid_confidence()` — calls `remember` with `confidence=1.5`, asserts response matches `"Invalid confidence value 1.5: must be between 0.0 and 1.0."` and no node created

**Checkpoint**: `uv run pytest tests/integration/test_remember.py` should pass all 4 tests.

---

## Phase 4: User Story 3 — `recall` Round-Trip Tests (Priority: P1)

**Goal**: Verify the `recall` MCP tool response strings, semantic relevance, limit behavior, no-results path, and empty-query error path.

**Independent Test**: `uv run pytest tests/integration/test_recall.py`

- [X] T010 [P] [US3] Create `tests/integration/test_recall.py` with `test_recall_returns_matching_memory()`: stores a memory about a distinctive topic via `remember`, then calls `recall` with a semantically matching query, asserts `result.data.startswith("Found ")`; and `test_recall_limit_honored()`: stores 3 distinct memories via `remember`, calls `recall` with `limit=2`, asserts the response contains at most 2 results (count "1." and "2." in `result.data`, assert no "3.")
- [X] T011 [US3] Add edge-case tests to `tests/integration/test_recall.py`: `test_recall_no_results()` — on a clean database (ensured by `clean_db` autouse), calls `recall` with query `"quantum entanglement"`, asserts `result.data == 'No memories found for "quantum entanglement".'`; `test_recall_empty_query()` — calls `recall` with `query=""`, asserts `result.data == "Query cannot be empty."`

**Checkpoint**: `uv run pytest tests/integration/test_recall.py` should pass all 4 tests.

---

## Phase 5: User Story 4 — Lifespan Schema Artifact Tests (Priority: P2)

**Goal**: Confirm the MCP server lifespan hook creates the required Neo4j vector index and uniqueness constraint against the real testcontainer.

**Independent Test**: Exercised via the session-scoped `client` fixture; `uv run pytest tests/integration/test_lifespan.py`

- [X] T012 [P] [US4] Create `tests/integration/test_lifespan.py` with two tests that receive `neo4j_driver` as a parameter: `test_vector_index_created()` — runs `SHOW INDEXES WHERE type = 'VECTOR' AND name = 'memory_embedding_index'`, asserts `records.single() is not None`; `test_uniqueness_constraint_created()` — runs `SHOW CONSTRAINTS WHERE name = 'memory_id_unique'`, asserts `records.single() is not None`

**Checkpoint**: `uv run pytest tests/integration/test_lifespan.py` should pass both tests.

---

## Phase 6: Polish & Cross-Cutting Concerns (US1 Completion)

**Purpose**: Update AGENTS.md so it becomes the single source of truth for agent onboarding and run the full suite to validate the pass/fail signal (US1).

- [X] T013 [P] Update `AGENTS.md` per FR-011: add `## Prerequisites` section listing Docker, `uv`, and `uv sync --all-groups`; restructure `## Testing` section to state that `uv run pytest` runs both unit and integration tests, include the integration-only command `uv run pytest tests/integration/`, and add an explicit note that integration tests are incompatible with `pytest-xdist` and must run sequentially; add a pointer to constitutional principles in `## Development Philosophy`
- [X] T014 Run `uv run pytest tests/integration/` and confirm all 10 tests match the expected output in `specs/004-tier1-integration-tests/quickstart.md`; then run `uv run pytest` to confirm the full suite (unit + integration) exits 0; bump version in `pyproject.toml` (patch increment)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001–T003) — **BLOCKS all test phases**
- **US2 (Phase 3)**: Depends on Phase 2 completion
- **US3 (Phase 4)**: Depends on Phase 2 completion — independent of Phase 3 (different file)
- **US4 (Phase 5)**: Depends on Phase 2 completion — independent of Phases 3 and 4 (different file)
- **Polish (Phase 6)**: Depends on all test phases being complete

### User Story Dependencies

- **US2 (P1)**: Can start after Phase 2 — no dependency on US3 or US4
- **US3 (P1)**: Can start after Phase 2 — no dependency on US2 or US4
- **US4 (P2)**: Can start after Phase 2 — no dependency on US2 or US3
- **US1**: Satisfied when all other user stories are complete and `uv run pytest` exits 0

### Within Each User Story

- `conftest.py` (Phase 2) must be complete before any test file
- Within a test file: `T008` creates the file → `T009` adds to it (sequential, same file)
- `T010` creates `test_recall.py` → `T011` adds to it (sequential, same file)
- `T012` creates `test_lifespan.py` (single task, complete standalone)

---

## Parallel Opportunities

### Phase 1

```bash
# T003 can run in parallel with T001 and T002 (different file):
Task: "T001 — add testcontainers dep to pyproject.toml"
Task: "T003 — create tests/integration/__init__.py"   # parallel with T001/T002
```

### After Phase 2 Completes (Multi-developer)

```bash
# All three test files can be written simultaneously:
Developer A: T008 → T009  (test_remember.py)
Developer B: T010 → T011  (test_recall.py)
Developer C: T012          (test_lifespan.py)
```

### Polish Phase

```bash
# T013 (AGENTS.md) can run in parallel with T008–T012:
Task: "T013 — update AGENTS.md"   # different file, no test dependencies
```

---

## Implementation Strategy

### MVP First (User Story 2 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational conftest.py (T004–T007) — **critical blocker**
3. Complete Phase 3: US2 remember tests (T008–T009)
4. **STOP and VALIDATE**: `uv run pytest tests/integration/test_remember.py` — all 4 pass
5. Continue with US3 and US4 for full coverage

### Incremental Delivery

1. T001–T003: Setup → Foundation ready to build
2. T004–T007: `conftest.py` → Infrastructure for all stories
3. T008–T009: `test_remember.py` → US2 complete, independently testable
4. T010–T011: `test_recall.py` → US3 complete, independently testable
5. T012: `test_lifespan.py` → US4 complete, independently testable
6. T013–T014: AGENTS.md + full validation → US1 satisfied, feature ships

---

## Notes

- [P] tasks = different files, no mutual dependencies
- [Story] label maps each task to a user story for traceability
- All conftest.py tasks (T004–T007) edit the same file — write them sequentially
- `clean_db` is `autouse=True` — all tests automatically get a clean database; no manual cleanup calls needed in test bodies
- Session-scoped async fixtures **must** use `@pytest_asyncio.fixture(scope="session", loop_scope="session")` — omitting `loop_scope` raises `ScopeMismatch` in pytest-asyncio 1.x
- Do not add `@pytest.mark.asyncio` to test functions — `asyncio_mode = "auto"` handles this globally
- The `mcp` import in `conftest.py` is safe at module level — `Config()` is not instantiated at import time; it runs inside the lifespan function when `async with Client(mcp)` is entered
