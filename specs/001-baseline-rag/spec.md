# Feature Specification: Baseline RAG - Store & Recall Memories

**Feature Branch**: `001-baseline-rag`
**Created**: 2025-12-24
**Status**: Draft
**Input**: User description: "Baseline RAG - Create Memory node type in Neo4j with vector-indexed content field. Store memories with vector embeddings using existing embedding provider."

## Clarifications

### Session 2025-12-24

- Q: What is the maximum memory text length and behavior when exceeded? → A: Reject text exceeding 4,000 characters with error message; limit is configurable via config file.
- Q: What format for Memory unique identifiers? → A: UUID
- Q: Which embedding model to use? → A: Use the model already configured in unit tests (keep simple)
- Q: MCP tool name? → A: `remember`
- Q: Observability requirements? → A: Deferred - out of scope for this barebones feature

### Session 2026-03-01

- Q: Is the `confidence` parameter in the `remember` tool required or optional? → A: Required — caller must always supply a confidence value.
- Q: What similarity metric should the Neo4j vector index use? → A: Cosine (default), configurable via application configuration.
- Q: What should the `remember` tool return on success? → A: Plain text confirmation string (e.g., `"Memory stored with id: <uuid>"`).
- Q: Should the embedding vector dimension be hardcoded or configurable? → A: Configurable via application configuration; default is 384 to match `sentence-transformers/all-MiniLM-L6-v2`.
- Q: What error format should validation failures (e.g., invalid confidence) return? → A: Plain text error string — consistent with FR-011/FR-012.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Store a Memory (Priority: P1)

An LLM client user speaks to their assistant and wants to store a piece of information for later recall. The user says something like "My favorite color is blue" and expects the system to remember this fact. The assistant calls the MCP tool to store this as a Memory in the database with a vector embedding that will enable future semantic search.

**Why this priority**: This is the foundational capability - without storing memories with proper vector indexing, no RAG functionality is possible. This enables the core value proposition of persistent memory.

**Independent Test**: Can be fully tested by calling the store MCP tool with a raw memory string and verifying the Memory is created in Neo4j with proper vector embedding stored in a vector index.

**Acceptance Scenarios**:

1. **Given** an empty database, **When** the user stores "My favorite color is blue", **Then** a Memory node is created containing the raw text and a vector embedding is generated and stored.
2. **Given** a database with existing Memories, **When** the user stores a new memory, **Then** a new Memory node is created without affecting existing ones.
3. **Given** a valid memory text, **When** the store operation completes, **Then** the system returns a plain-text confirmation string containing the created Memory's UUID (e.g., `"Memory stored with id: <uuid>"`).
4. **Given** the first Memory is being stored, **When** the store operation runs, **Then** the system ensures a vector index exists on the Memory node's embedding field (creating it if necessary).
5. **Given** a memory text, **When** the embedding is generated, **Then** the existing embedding provider infrastructure is used to create the vector.

---

### Edge Cases

- **Empty or whitespace-only memory**: Rejected with clear error message (FR-006).
- **Memory text exceeds maximum length**: Rejected with error message stating the configurable limit (FR-007).
- **Embedding service unavailable**: Operation fails; MCP tool returns a plain-text error message (FR-011; see `contracts/remember-tool.md`).
- **Special characters or unicode in memory text**: Accepted and stored as-is (valid input).
- **Neo4j database connection fails**: Operation fails; MCP tool returns a plain-text error message (FR-012; see `contracts/remember-tool.md`).

---

### User Story 2 - Recall Memories (Priority: P1)

An LLM client user wants to retrieve previously stored memories relevant to their current context. The user asks something like "What do I know about colors?" and the assistant calls the `recall` MCP tool with a query string. The system generates a vector embedding of the query, performs similarity search against stored memories, and returns the most relevant results as a plain-text list.

**Why this priority**: Recall completes the RAG loop. Without retrieval, stored memories have no utility. Store + recall together constitute the minimum viable persistent memory capability.

**Independent Test**: Can be fully tested by calling the `recall` MCP tool with a query string and verifying that semantically relevant memories are returned in order of similarity.

**Acceptance Scenarios**:

1. **Given** memories exist in the database, **When** the user calls `recall` with a relevant query, **Then** the most semantically similar memories are returned ordered by similarity score (descending).
2. **Given** no memories in the database, **When** the user calls `recall` with any query, **Then** a graceful "no results" message is returned (not an error).
3. **Given** an empty or whitespace-only query, **When** the user calls `recall`, **Then** a plain-text validation error is returned.
4. **Given** a query with `limit=3`, **When** `recall` runs, **Then** at most 3 results are returned.
5. **Given** an embedding provider failure, **When** `recall` is called, **Then** a plain-text error message is returned without propagating the exception.
6. **Given** a Neo4j failure, **When** `recall` is called, **Then** a plain-text error message is returned without propagating the exception.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose the MCP server via HTTP transport.
- **FR-002**: System MUST provide an MCP tool named `remember` that accepts two required parameters — `content` (raw memory text) and `confidence` (float, 0.0–1.0) — and stores them as a Memory.
- **FR-003**: System MUST generate a vector embedding for each stored Memory using the existing `IEmbeddingProvider` infrastructure.
- **FR-004**: System MUST persist Memories in Neo4j as nodes with the vector embedding stored in an indexed field.
- **FR-005**: System MUST ensure a vector index exists on the Memory embedding field (creating it on first use if necessary).
- **FR-006**: System MUST reject empty or whitespace-only memory text with a plain-text error message returned to the MCP client.
- **FR-007**: System MUST reject memory text exceeding the configured maximum length (default: 4,000 characters) with a plain-text error message stating the limit, returned to the MCP client.
- **FR-008**: The maximum memory text length MUST be configurable via application configuration (not hardcoded).
- **FR-014**: The MCP server host and port MUST be configurable via application configuration with sensible defaults (`0.0.0.0:8000`).
- **FR-009**: Each Memory MUST be assigned a UUID upon creation.
- **FR-010**: Each Memory MUST record three timestamps — `created_at`, `updated_at`, and `accessed_at` — all set to the same UTC value at creation time.
- **FR-011**: System MUST handle embedding provider failures by returning a plain-text error message string to the MCP client; the raw exception MUST NOT propagate unhandled.
- **FR-012**: System MUST handle Neo4j connection failures by returning a plain-text error message string to the MCP client; the raw exception MUST NOT propagate unhandled.
- **FR-013**: System MUST reject confidence values outside the range [0.0, 1.0] with a plain-text error message returned to the MCP client (consistent with FR-011/FR-012).
- **FR-015**: The Neo4j vector index MUST use cosine similarity. The similarity metric is fixed at index creation time and is not runtime-configurable.
- **FR-016**: On success, the `remember` tool MUST return a plain-text confirmation string containing the created Memory's UUID (e.g., `"Memory stored with id: <uuid>"`).
- **FR-018**: System MUST provide an MCP tool named `recall` that accepts a `query` string (required) and an optional `limit` integer (default: 10) and returns semantically similar memories.
- **FR-019**: System MUST generate a vector embedding for the search query using the existing `IEmbeddingProvider` infrastructure.
- **FR-020**: System MUST perform vector similarity search against the Neo4j vector index and return results ordered by similarity score (descending).
- **FR-021**: System MUST return at most `limit` results; if fewer matches exist, return only what is available.
- **FR-022**: System MUST handle `recall` tool errors (embedding failure, DB failure, empty query) by returning a plain-text error message string; exceptions MUST NOT propagate unhandled.
- **FR-023**: System MUST reject `recall` tool `limit` values less than 1 with a plain-text error message returned to the MCP client.

### Key Entities

- **Memory**: The core entity representing a stored memory. Contains the raw memory text (exact words from the user in the `content` field), a vector embedding of that text, a UUID identifier, confidence score (0.0-1.0 scale indicating memory reliability), and timestamps for creation, last update, and last access. This is a Neo4j node type with a vector index on the embedding field that enables semantic search via the `recall` tool.

## Assumptions

- The existing `IEmbeddingProvider` and `LocalEmbeddingProvider` are functional and will be used for generating embeddings, using the same model configured in unit tests.
- Neo4j database is available and properly configured with vector index capabilities.
- MCP client is responsible for calling the tools; no direct user interface is provided.
- Memory text will typically be short-to-medium length statements (under 4,000 characters).
- Single-tenant usage for this baseline implementation (no user isolation).
- Search results are ordered by vector similarity score; no re-ranking or filtering beyond the top-K limit.

## Out of Scope

- Graph relationships between Memories (triples, subject-predicate-object)
- Memory deduplication or conflict detection
- Memory supersession or update/delete operations
- Entity graph extraction from raw memories
- Multi-tenant user isolation
- Re-ranking, filtering, or metadata-based search beyond vector similarity

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of stored Memories have a valid vector embedding persisted alongside the raw text.
- **SC-002**: The vector index is automatically created on first Memory storage if it doesn't exist.
- **SC-003**: Invalid inputs (empty text, whitespace-only, exceeds max length, invalid confidence) are rejected with clear error messages 100% of the time.
- **SC-004**: Errors from the embedding provider or database are returned as plain-text error messages to the MCP client — no unhandled exception propagates.
- **SC-005**: `recall` returns results ordered by similarity score (highest first); the result count never exceeds the requested `limit`.
- **SC-006**: An empty or whitespace-only query to `recall` is rejected with a plain-text error message.
- **SC-007**: `recall` with no matching memories returns a graceful plain-text "no results" message (not an error condition).
