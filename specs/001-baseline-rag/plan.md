# Implementation Plan: Baseline RAG - Store & Recall Memories

**Branch**: `001-baseline-rag` | **Date**: 2025-12-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-baseline-rag/spec.md`

## Summary

Implement the baseline RAG capability: two MCP tools — `remember` (store) and `recall` (search) — that together provide a complete read/write memory loop. `remember` stores memory text and confidence score as a Memory node in Neo4j with a vector embedding. `recall` accepts a query string, generates a query embedding using the same `IEmbeddingProvider`, and performs vector similarity search against stored memories. The existing `Memory` dataclass is kept as-is with `source` defaulting to `"user_requested"` and supersession fields defaulting to `None` (supersession is out of scope). The embedding uses `LocalEmbeddingProvider` with `all-MiniLM-L6-v2` (384-dimensional vectors, configurable). The MCP server is exposed via HTTP transport. The vector index uses cosine similarity (configurable).

## Technical Context

**Language/Version**: Python 3.10+ (per pyproject.toml `requires-python = ">=3.10"`)
**Primary Dependencies**: FastMCP 2.11+, Neo4j driver 5.28+, sentence-transformers 5.1+, Pydantic 2.11+
**Storage**: Neo4j (graph database with vector index capabilities)
**Testing**: pytest 8.4+ with pytest-asyncio
**Target Platform**: Linux server (MCP server)
**Project Type**: Single project
**Constraints**: Max memory text length configurable (default 4,000 characters); MCP host/port configurable with defaults; vector index uses 384 dimensions and cosine similarity (both fixed at index creation time — see TD-002)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. YAGNI** | PASS | Implementing store (`remember`) and search (`recall`) — both required by spec; no supersession, entity graph, or other speculative features |
| **II. KISS** | PASS | Simple flows: validate → embed → store; validate → embed → search; no premature abstractions |
| **III. Established Patterns** | PASS | Using Factory (embedding), Repository (Neo4j), Interface Segregation (IEmbeddingProvider) |
| **IV. Layered Architecture** | PASS | MCP Server → Service → Repository → Provider; dependencies flow down |
| **V. Mandatory Testing** | GATE | Tests must pass after each implementation phase |
| **VI. TDD** | GATE | Tests must be written before implementation code |

**Quality Gates to enforce during implementation:**
1. Code Gate: No unused code, no "might need later" features
2. Pattern Gate: Repository pattern for Neo4j, Factory for embeddings
3. Architecture Gate: Service layer orchestrates; Repository handles DB
4. TDD Gate: Failing tests exist before implementation
5. Test Gate: `uv run pytest` passes with no failures
6. Clean Code Gate: No dead code, no TODO comments

## Project Structure

### Documentation (this feature)

```text
specs/001-baseline-rag/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── embeddings/
│   ├── __init__.py
│   ├── base.py                    # IEmbeddingProvider interface [EXISTS]
│   └── local_embedding_provider.py # LocalEmbeddingProvider [EXISTS]
├── graph/
│   ├── __init__.py
│   ├── base.py                    # [EMPTY - need repository interface]
│   └── neo4j.py                   # [EMPTY - need Neo4jRepository]
├── mcp/
│   ├── __init__.py
│   └── server.py                  # [EMPTY - need MCP server with remember and recall tools]
├── memory/
│   ├── __init__.py
│   └── service.py                 # [EMPTY - need MemoryService]
├── models/
│   ├── __init__.py
│   └── memory.py                  # [UPDATE - set source default to "user_requested"]
└── utils/
    ├── __init__.py
    ├── config.py                  # Config class [EXISTS - need to extend]
    └── factory.py                 # Factory class [EXISTS]

tests/
├── test_embeddings/               # [EXISTS]
├── test_graph/
│   ├── __init__.py
│   └── test_neo4j.py              # [EMPTY - need repository tests]
├── test_mcp/
│   ├── __init__.py
│   └── test_server.py             # [NEW - MCP tool tests]
├── test_memory/
│   ├── __init__.py
│   └── test_service.py            # [EMPTY - need service tests]
└── test_models/
    ├── __init__.py
    └── test_memory.py             # [UPDATE - update for simplified model]
```

**Structure Decision**: Single project structure. New components will be added to existing `src/` directories following the established layered architecture.

## Complexity Tracking

No constitution violations requiring justification. The design follows YAGNI/KISS principles:
- Two MCP tools: `remember` (store) and `recall` (search) — both required by spec; no supersession, entity graph, or other speculative tools
- Memory entity uses existing dataclass without structural changes; supersession fields remain at `None` defaults and are out of scope
- Direct Neo4j operations via repository pattern; `search_memories` uses the existing vector index
- Leverages existing embedding infrastructure for both store and query embedding generation
