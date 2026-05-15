# Data Model: Tier-1 Integration Tests

**Branch**: `004-tier1-integration-tests`

This document describes the entities the integration tests read and write. No new entities are introduced — tests exercise the existing Memory node schema.

---

## Memory Node (Neo4j)

Persisted by `Neo4jRepository.create_memory()`. Label: `Memory`.

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | String | No | UUID v4; unique (enforced by `memory_id_unique` constraint) |
| `content` | String | No | Raw text of the memory |
| `embedding` | Float[] | No | 384-dimensional cosine vector |
| `confidence` | Float | No | Confidence score in [0.0, 1.0] |
| `created_at` | DateTime | No | UTC timestamp of creation |
| `updated_at` | DateTime | No | UTC timestamp of last update |
| `accessed_at` | DateTime | No | UTC timestamp of last retrieval |
| `source` | String | No | Origin tag; default `"user_requested"` |
| `supersedes` | String | Yes | ID of the memory this replaces (`null` if none) |
| `superseded_by` | String | Yes | ID of the memory that replaces this (`null` if none) |

**Total: 10 fields stored per node.** Integration tests assert that all 10 are present after a `remember` call.

---

## Schema Artifacts (Neo4j)

Created by `Neo4jRepository.ensure_vector_index()` during the MCP server lifespan.

| Artifact | Type | Target | Details |
|----------|------|--------|---------|
| `memory_embedding_index` | Vector Index | `Memory.embedding` | 384 dims, cosine similarity |
| `memory_id_unique` | Uniqueness Constraint | `Memory.id` | Prevents duplicate IDs |

Both are created with `IF NOT EXISTS` — safe to call repeatedly (idempotent).

---

## Test Entities

| Entity | Scope | Description |
|--------|-------|-------------|
| `Neo4jContainer` | Session | Testcontainers-managed Neo4j 2026.03.1 instance |
| `Client` (FastMCP) | Session | In-memory MCP client; opens lifespan on context entry |
| Per-test cleanup | Function | `MATCH (n:Memory) DETACH DELETE n` — removes data, preserves schema |
