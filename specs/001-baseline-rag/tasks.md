# Tasks: Baseline RAG - Store & Recall Memories

**Input**: Design documents from `/specs/001-baseline-rag/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Following TDD (Constitution Principle VI) - Tests MUST be written BEFORE implementation code

**Organization**: Two user stories (P1 - Store a Memory, P1 - Recall Memories) broken into layers following the established architecture

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: User Story 1 - Store a Memory
- **[US2]**: User Story 2 - Recall Memories
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and configuration

- [X] T001 Extend Config class with max_memory_length, mcp_host, mcp_port fields in src/utils/config.py (FR-008, FR-014)
- [X] T002 Update .env.example with new config fields (max_memory_length, mcp_host, mcp_port) with default values
- [X] T003 [P] Create tests/test_mcp/__init__.py directory structure
- [X] T004 [P] Create tests/test_models/__init__.py directory structure (if not exists)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Set `source: str = "user_requested"` as default in Memory dataclass in src/models/memory.py
- [X] T006 [P] Create IGraphRepository interface in src/graph/base.py with create_memory, ensure_vector_index, and search_memories methods
- [X] T007 Run `uv run pytest` to verify existing embedding tests still pass after config changes

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Store a Memory (Priority: P1) 🎯 MVP

**Goal**: Enable LLM clients to store memories as Memory nodes with vector embeddings via HTTP MCP tool

**Independent Test**: Call the `remember` MCP tool via HTTP with content and confidence, verify Memory node created in Neo4j with 384-dimensional embedding

### Tests for User Story 1 (TDD - Write First, Watch Fail) ⚠️

> **CONSTITUTION PRINCIPLE VI**: These tests MUST be written FIRST and MUST FAIL before writing implementation

#### Memory Model Tests

- [X] T008 [P] [US1] Write test_memory_creation in tests/test_models/test_memory.py - verify Memory with all 10 fields
- [X] T009 [P] [US1] Write test_memory_field_types in tests/test_models/test_memory.py - verify id is str, content is str, embedding is list[float], confidence is float, source is str, supersedes/superseded_by are Optional[str], timestamps are datetime
- [X] T010 [P] [US1] Write test_memory_embedding_dimensions in tests/test_models/test_memory.py - verify embedding has exactly 384 dimensions

#### Repository Tests (Use Mocks - No Real Neo4j Connection)

- [X] T011 [P] [US1] Write test_neo4j_repository_init in tests/test_graph/test_neo4j.py - verify Neo4jRepository initialization with driver (mock GraphDatabase.driver)
- [X] T012 [P] [US1] Write test_create_memory_success in tests/test_graph/test_neo4j.py - mock session.run, verify correct Cypher query and parameters
- [X] T013 [P] [US1] Write test_ensure_vector_index_creates_index in tests/test_graph/test_neo4j.py - mock session.run, verify vector index creation Cypher (384 dimensions, cosine similarity) and uniqueness constraint Cypher on Memory.id
- [X] T014 [P] [US1] Write test_ensure_vector_index_idempotent in tests/test_graph/test_neo4j.py - mock session.run, verify IF NOT EXISTS pattern
- [X] T015 [P] [US1] Write test_create_memory_with_all_fields in tests/test_graph/test_neo4j.py - mock session.run, verify all 10 Memory fields in Cypher parameters
- [X] T016 [P] [US1] Write test_repository_close in tests/test_graph/test_neo4j.py - mock driver, verify driver.close() is called on Neo4jRepository.close() (TDD gate for T039)
- [X] T017 [P] [US1] Write test_create_memory_neo4j_failure in tests/test_graph/test_neo4j.py - mock session.run to raise ServiceUnavailable, verify exception propagates from repository (FR-012)

#### Service Tests

- [X] T018 [P] [US1] Write test_memory_service_init in tests/test_memory/test_service.py - verify MemoryService initialization with config, embedder, repository
- [X] T019 [P] [US1] Write test_store_memory_success in tests/test_memory/test_service.py - mock embedder and repository, verify successful memory storage with UUID generation
- [X] T020 [P] [US1] Write test_store_memory_empty_text_rejected in tests/test_memory/test_service.py - verify ValueError for empty content
- [X] T021 [P] [US1] Write test_store_memory_whitespace_rejected in tests/test_memory/test_service.py - verify ValueError for whitespace-only content
- [X] T022 [P] [US1] Write test_store_memory_exceeds_max_length in tests/test_memory/test_service.py - verify ValueError for content exceeding max_memory_length
- [X] T023 [P] [US1] Write test_store_memory_confidence_validation in tests/test_memory/test_service.py - verify ValueError for confidence < 0.0 or > 1.0
- [X] T024 [P] [US1] Write test_store_memory_generates_embedding in tests/test_memory/test_service.py - mock embedder, verify generate_embedding called with correct content
- [X] T025 [P] [US1] Write test_store_memory_sets_timestamps in tests/test_memory/test_service.py - verify created_at, updated_at, accessed_at all set to same value
- [X] T026 [P] [US1] Write test_store_memory_embedding_failure in tests/test_memory/test_service.py - mock embedder to raise RuntimeError, verify exception propagates from service (FR-011)

#### MCP Server Tests

- [X] T027 [P] [US1] Write test_mcp_server_registers_remember_tool in tests/test_mcp/test_server.py - verify tool registration
- [X] T028 [P] [US1] Write test_remember_tool_valid_input in tests/test_mcp/test_server.py - mock service, verify response is a plain-text str (not dict) containing "Memory stored with id:"
- [X] T029 [P] [US1] Write test_remember_tool_returns_memory_id in tests/test_mcp/test_server.py - mock service returning Memory with known UUID, verify UUID appears in the plain-text response string
- [X] T030 [P] [US1] Write test_remember_tool_returns_str_type in tests/test_mcp/test_server.py - mock service, verify return type is str (guards against accidentally returning dict)
- [X] T031 [P] [US1] Write test_remember_tool_empty_memory_error in tests/test_mcp/test_server.py - mock service to raise ValueError, verify error string returned (not raised)
- [X] T032 [P] [US1] Write test_remember_tool_exceeds_max_length_error in tests/test_mcp/test_server.py - mock service to raise ValueError, verify error string returned
- [X] T033 [P] [US1] Write test_remember_tool_invalid_confidence_error in tests/test_mcp/test_server.py - mock service to raise ValueError, verify error string returned
- [X] T034 [P] [US1] Write test_remember_tool_embedding_failure in tests/test_mcp/test_server.py - mock service to raise RuntimeError, verify error string returned (not raised) (FR-011)
- [X] T035 [P] [US1] Write test_remember_tool_neo4j_failure in tests/test_mcp/test_server.py - mock service to raise Exception, verify error string returned (not raised) (FR-012)

**TDD Checkpoint**: Run `uv run pytest` - ALL tests should FAIL (RED phase) ❌

---

### Implementation for User Story 1 (Make Tests Pass)

> **CONSTITUTION PRINCIPLE VI**: Implement ONLY enough code to make the failing tests pass (GREEN phase)

#### Repository Layer

- [X] T036 [US1] Implement Neo4jRepository.__init__ in src/graph/neo4j.py - create driver instance with URI, user, password
- [X] T037 [US1] Implement Neo4jRepository.ensure_vector_index in src/graph/neo4j.py - execute CREATE VECTOR INDEX Cypher with IF NOT EXISTS using hardcoded 384 dimensions and cosine similarity; also execute CREATE CONSTRAINT IF NOT EXISTS for uniqueness on Memory.id property (FR-015)
- [X] T038 [US1] Implement Neo4jRepository.create_memory in src/graph/neo4j.py - execute CREATE node Cypher with all 10 Memory fields
- [X] T039 [US1] Implement Neo4jRepository.close in src/graph/neo4j.py - close driver connection
- [X] T040 [US1] Run `uv run pytest tests/test_graph/` - verify repository tests pass ✅

#### Service Layer

- [X] T041 [US1] Implement MemoryService.__init__ in src/memory/service.py - store config, embedder, repository dependencies
- [X] T042 [US1] Implement MemoryService._validate_content in src/memory/service.py - check empty, whitespace, max_length; raise ValueError with clear message
- [X] T043 [US1] Implement MemoryService._validate_confidence in src/memory/service.py - check 0.0 <= confidence <= 1.0; raise ValueError with clear message
- [X] T044 [US1] Implement MemoryService.store_memory in src/memory/service.py - validate, generate embedding, create Memory, persist
- [X] T045 [US1] Add UUID generation (uuid.uuid4()) in MemoryService.store_memory in src/memory/service.py
- [X] T046 [US1] Add timestamp generation (datetime.now(timezone.utc)) for all 3 timestamp fields in src/memory/service.py
- [X] T047 [US1] Run `uv run pytest tests/test_memory/` - verify service tests pass ✅

#### MCP Server Layer

- [X] T048 [US1] Create FastMCP instance in src/mcp/server.py - initialize with name "Memento"
- [X] T049 [US1] Register `remember` tool with @mcp.tool() decorator in src/mcp/server.py
- [X] T050 [US1] Implement remember tool function in src/mcp/server.py - accept content (str) and confidence (float) parameters
- [X] T051 [US1] Wire remember tool to MemoryService.store_memory in src/mcp/server.py
- [X] T052 [US1] Format tool success response as plain-text string: `f"Memory stored with id: {memory.id}"` in src/mcp/server.py (see contracts/remember-tool.md; FR-016)
- [X] T053 [US1] Wrap remember tool body in try/except: catch ValueError → return str(e); catch all other exceptions → return generic error string; no exception may propagate unhandled (FR-011, FR-012; see contracts/remember-tool.md)
- [X] T054 [US1] Add FastMCP HTTP server startup in src/mcp/server.py __main__ block using `mcp.run(transport="http", host=config.mcp_host, port=config.mcp_port)` (FR-001, FR-014)
- [X] T055 [US1] Run `uv run pytest tests/test_mcp/` - verify MCP tool tests pass ✅

**TDD Checkpoint**: Run `uv run pytest` - ALL tests should PASS (GREEN phase) ✅

**Checkpoint**: User Story 1 is fully functional, tested, and ready for production

---

## Phase 3 cont.: User Story 2 - Recall Memories (Priority: P1) 🎯

**Goal**: Enable LLM clients to semantically search stored memories via HTTP MCP tool

**Independent Test**: Call the `recall` MCP tool via HTTP with a query string, verify relevant Memory nodes are returned ordered by similarity score

### Tests for User Story 2 (TDD - Write First, Watch Fail) ⚠️

> **CONSTITUTION PRINCIPLE VI**: These tests MUST be written FIRST and MUST FAIL before writing implementation

#### Repository Tests (Use Mocks - No Real Neo4j Connection)

- [X] T064 [P] [US2] Write test_search_memories_returns_results in tests/test_graph/test_neo4j.py - mock session.run to return records with node and score, verify correct vector search Cypher executed with embedding and limit parameters
- [X] T065 [P] [US2] Write test_search_memories_empty_results in tests/test_graph/test_neo4j.py - mock session.run returning empty list, verify empty list returned from repository
- [X] T066 [P] [US2] Write test_search_memories_returns_ordered_results in tests/test_graph/test_neo4j.py - mock session returning multiple records, verify results list preserves order from Neo4j response

#### Service Tests

- [X] T067 [P] [US2] Write test_search_memory_success in tests/test_memory/test_service.py - mock embedder and repository (returning [(Memory, 0.9)]), verify service returns list[tuple[Memory, float]] directly with no field selection
- [X] T068 [P] [US2] Write test_search_memory_empty_query_rejected in tests/test_memory/test_service.py - verify ValueError for empty query string
- [X] T069 [P] [US2] Write test_search_memory_whitespace_rejected in tests/test_memory/test_service.py - verify ValueError for whitespace-only query
- [X] T070 [P] [US2] Write test_search_memory_generates_embedding in tests/test_memory/test_service.py - mock embedder, verify generate_embedding called with the query text
- [X] T071 [P] [US2] Write test_search_memory_embedding_failure in tests/test_memory/test_service.py - mock embedder to raise RuntimeError, verify exception propagates from service (FR-022)
- [X] T072 [P] [US2] Write test_search_memory_no_results in tests/test_memory/test_service.py - mock repository returning empty list, verify empty list returned from service
- [X] T089 [P] [US2] Write test_search_memory_invalid_limit in tests/test_memory/test_service.py - verify ValueError("Limit must be at least 1.") raised when limit < 1 (FR-023)

#### MCP Server Tests

- [X] T073 [P] [US2] Write test_mcp_server_registers_recall_tool in tests/test_mcp/test_server.py - verify recall tool registered alongside remember tool
- [X] T074 [P] [US2] Write test_recall_tool_valid_input in tests/test_mcp/test_server.py - mock service returning [(mock_memory, 0.9)], verify response is plain-text str containing result content
- [X] T075 [P] [US2] Write test_recall_tool_no_results in tests/test_mcp/test_server.py - mock service returning empty list, verify response contains "No memories found" (not an error string)
- [X] T076 [P] [US2] Write test_recall_tool_empty_query_error in tests/test_mcp/test_server.py - mock service to raise ValueError, verify error string returned (not raised)
- [X] T077 [P] [US2] Write test_recall_tool_embedding_failure in tests/test_mcp/test_server.py - mock service to raise RuntimeError, verify error string returned (not raised) (FR-022)
- [X] T078 [P] [US2] Write test_recall_tool_neo4j_failure in tests/test_mcp/test_server.py - mock service to raise Exception, verify error string returned (not raised) (FR-022)
- [X] T079 [P] [US2] Write test_recall_tool_respects_limit in tests/test_mcp/test_server.py - mock service, verify limit parameter passed through to service.search_memory
- [X] T090 [P] [US2] Write test_recall_tool_invalid_limit in tests/test_mcp/test_server.py - mock service to raise ValueError for limit=0, verify error string returned (not raised) (FR-023)

**TDD Checkpoint**: Run `uv run pytest` - ALL US2 tests should FAIL (RED phase) ❌ *(includes T089, T090)*

---

### Implementation for User Story 2 (Make Tests Pass)

> **CONSTITUTION PRINCIPLE VI**: Implement ONLY enough code to make the failing tests pass (GREEN phase)

#### Repository Layer

- [X] T080 [US2] Implement Neo4jRepository.search_memories in src/graph/neo4j.py - execute `CALL db.index.vector.queryNodes('memory_embedding_index', $limit, $embedding) YIELD node AS m, score RETURN m, score` Cypher; return list of (Memory, float) tuples
- [X] T081 [US2] Run `uv run pytest tests/test_graph/` - verify all repository tests pass ✅

#### Service Layer

- [X] T082 [US2] Implement MemoryService._validate_query in src/memory/service.py - check non-empty, non-whitespace; raise ValueError("Query cannot be empty.")
- [X] T091 [US2] Implement limit validation in MemoryService.search_memory in src/memory/service.py - raise ValueError("Limit must be at least 1.") when limit < 1 (FR-023)
- [X] T083 [US2] Implement MemoryService.search_memory in src/memory/service.py - validate query and limit, generate embedding via embedder, call repository.search_memories, return list[tuple[Memory, float]] directly — no field selection or dict conversion
- [X] T084 [US2] Run `uv run pytest tests/test_memory/` - verify all service tests pass ✅

#### MCP Server Layer

- [X] T085 [US2] Register `recall` tool with @mcp.tool() decorator in src/mcp/server.py - accept query (str) and limit (int = 10) parameters
- [X] T086 [US2] Implement recall tool body in src/mcp/server.py - call service.search_memory(query, limit), format results as plain-text via tuple unpacking `for memory, score in results` using the pattern from contracts/recall-tool.md
- [X] T087 [US2] Wrap recall tool in try/except: ValueError → return str(e); all other exceptions → return generic error string; no exception may propagate unhandled (FR-022; see contracts/recall-tool.md)
- [X] T088 [US2] Run `uv run pytest tests/test_mcp/` - verify all MCP tool tests pass ✅

**TDD Checkpoint**: Run `uv run pytest` - ALL tests should PASS (GREEN phase) ✅

**Checkpoint**: User Story 2 is fully functional, tested, and ready for production

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and documentation

- [X] T056 [P] Review code for YAGNI violations - remove any unused code or speculative features
- [X] T057 [P] Review code for KISS violations - simplify any over-engineered solutions
- [X] T058 [P] Verify layered architecture - ensure no lower layers depend on upper layers
- [X] T059 [P] Check for TODO comments - remove or link to issues
- [X] T060 [P] Verify all imports are used - remove unused imports
- [X] T061 Run `uv run pytest --cov=src --cov-report=term-missing` - verify ≥80% test coverage for new code
- [X] T062 Run quickstart.md validation end-to-end - verify all documented steps work

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 3 cont.)**: Depends on User Story 1 completion (search requires the vector index that US1 creates)
- **Polish (Phase 4)**: Depends on User Story 2 completion

### Within User Story 1

**TDD Cycle (Constitution Principle VI):**
1. **RED**: Write all tests first (T008-T035, T064-T079, T089-T090) - tests FAIL ❌
2. **GREEN**: Implement code to make tests pass (T036-T055, T080-T088, T091) - tests PASS ✅
3. **REFACTOR**: Polish (T056-T062) - tests still PASS ✅

**Layer Dependencies:**
- Repository tests (T011-T017, T064-T066) before Repository implementation (T036-T040, T080-T081)
- Service tests (T018-T026, T067-T072, T089) before Service implementation (T041-T047, T082-T084, T091)
- MCP tests (T027-T035, T073-T079, T090) before MCP implementation (T048-T055, T085-T088)

### Parallel Opportunities

- **Setup tasks (Phase 1)**: T001-T004 can run in parallel [P]
- **Test writing US1 (Phase 3)**: All test tasks T008-T035 can run in parallel [P] (different test files)
- **Test writing US2 (Phase 3 cont.)**: All test tasks T064-T079, T089-T090 can run in parallel [P] (different test files)
- **Polish tasks (Phase 4)**: T056-T060 can run in parallel [P] (review tasks); T061-T062 run sequentially

---

## Parallel Example: User Story 1 - Test Writing

```bash
# Launch all US1 test writing tasks together (TDD RED phase):
Task T008: "Write test_memory_creation in tests/test_models/test_memory.py"
# ... all test tasks T009-T035

# After all US1 tests written, verify they FAIL:
uv run pytest  # Expected: ALL FAIL (RED) ❌

# Then implement sequentially by layer:
# Repository (T036-T040) → Service (T041-T047) → MCP (T048-T055)
```

## Parallel Example: User Story 2 - Test Writing

```bash
# Launch all US2 test writing tasks together (TDD RED phase):
Task T064: "Write test_search_memories_returns_results in tests/test_graph/test_neo4j.py"
# ... all test tasks T065-T079, T089-T090

# After all US2 tests written, verify new tests FAIL (US1 tests still pass):
uv run pytest  # Expected: US1 PASS ✅, US2 FAIL ❌

# Then implement sequentially by layer:
# Repository search (T080-T081) → Service search (T082-T084, T091) → MCP recall (T085-T088)
```

---

## Implementation Strategy

### TDD Workflow (Constitution Mandated)

1. **Phase 1**: Setup → Update .env.example, extend Config, create test dirs
2. **Phase 2**: Foundational → Set Memory model source default, run `uv run pytest` (verify no regressions)
3. **Phase 3 US1 - RED**: Write ALL US1 tests (T008-T035) with mocks → Run `uv run pytest` → Verify ALL FAIL ❌
4. **Phase 3 US1 - GREEN**: Implement Repository (T036-T040) → Run `uv run pytest tests/test_graph/` → Verify PASS ✅
5. **Phase 3 US1 - GREEN**: Implement Service (T041-T047) → Run `uv run pytest tests/test_memory/` → Verify PASS ✅
6. **Phase 3 US1 - GREEN**: Implement MCP (T048-T055) → Run `uv run pytest tests/test_mcp/` → Verify PASS ✅
7. **Phase 3 US2 - RED**: Write ALL US2 tests (T064-T079, T089-T090) with mocks → Run `uv run pytest` → Verify new tests FAIL ❌
8. **Phase 3 US2 - GREEN**: Implement Repository search (T080-T081) → Service search (T082-T084, T091) → MCP recall (T085-T088) → Verify PASS ✅
9. **Phase 3 - VALIDATE**: Run `uv run pytest` → Verify ALL tests PASS ✅
10. **Phase 4**: Polish → Final `uv run pytest --cov=src --cov-report=term-missing` → Verify ≥80% coverage

### Quality Gates (Constitution Enforced)

After each implementation task:
1. **Code Gate**: No unused code, follows YAGNI/KISS
2. **Pattern Gate**: Repository pattern for Neo4j, Factory for embeddings
3. **Architecture Gate**: Service layer orchestrates, Repository handles DB
4. **TDD Gate**: Tests written before implementation; failing test exists before any new code
5. **Test Gate**: `uv run pytest` passes with no failures (tests use mocks)
6. **Clean Code Gate**: No dead code, no TODO comments

**Note**: All tests use mocks - no real Neo4j or embedding service required for the test suite to pass

### MVP Delivery

Both user stories are P1; MVP requires both to be complete:
- Setup + Foundational → Foundation ready
- User Story 1 (remember) complete → store capability delivered
- User Story 2 (recall) complete → MVP DELIVERED ✅ (full RAG loop: store + search)
- Polish → Production ready

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [US1] label = User Story 1 (Store a Memory)
- [US2] label = User Story 2 (Recall Memories)
- **TDD is MANDATORY** (Constitution Principle VI) - tests written BEFORE code
- **Test Gate** (Constitution Principle V) - `uv run pytest` MUST pass after each phase
- **All tests use mocks** - no real Neo4j connection required for test suite
- **.env.example** already exists - update it with new config fields (T002)
- Verify tests FAIL before implementation (RED)
- Verify tests PASS after implementation (GREEN)
- Refactor while keeping tests green (REFACTOR)
- Commit after each checkpoint or logical group
- Constitution compliance checked at Phase 4 polish tasks
- Store tool contract: contracts/remember-tool.md; Search tool contract: contracts/recall-tool.md
- `remember` success response is plain-text: `"Memory stored with id: <uuid>"` (FR-016)
- `recall` success response is plain-text: numbered list of results (see contracts/recall-tool.md)
