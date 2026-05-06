# Implementation Plan: 002-container-setup

**Branch**: `002-container-setup` (workspace branch: `feature/container-setup`) | **Date**: 2026-04-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-container-setup/spec.md`

## Summary

Implement ADR-007's container strategy for two of its three deployment targets — local power user and developer dev loop — and bake the embedding model into the published image as an interim resolution for TD-004. Cloud Run is deferred to a separate spec.

The work splits into five concrete deliverables:

1. **Refactor `src/mcp/server.py`** to a pure module: delete the `__main__` block, move expensive resource construction (`Config`, embedder, `Neo4jRepository`, `MemoryService`) into a FastMCP `lifespan` async context manager, and run `ensure_vector_index` from that lifespan (fixing the latent bug where dev `--reload` skips index creation). Drop `Config.mcp_host` / `Config.mcp_port` (TD-003 resolution).
2. **Multi-stage `Dockerfile`** using `uv` that bakes `sentence-transformers/all-MiniLM-L6-v2` to `/app/.cache/models`. `ENTRYPOINT ["fastmcp", "run", "src/mcp/server.py"]`, empty `CMD`, non-root user.
3. **`docker-compose.yml` at repo root** referencing `ghcr.io/rigrergl/memento:vX.Y.Z` (pinned, no `:latest`, no `build:`), wiring Neo4j + Memento with a Memento HTTP healthcheck and `127.0.0.1` port bindings.
4. **Dev-loop `.mcp.json`** wiring `uv run fastmcp run … --reload` plus `mcp-neo4j-cypher` for self-validation.
5. **GitHub Actions workflows**: `auto-tag.yml` (creates `vX.Y.Z` tag from `pyproject.toml` on `main`) and `publish.yml` (multi-arch `linux/amd64,linux/arm64` build → GHCR on tag push).

Documentation updates: README rewritten with Power-User + Developer sections including all three MCP-client config flavours; `Documentation/known-tech-debt.md` updated for TD-003 (resolved) and TD-004 (interim resolution noted).

Technical approach details and rejected alternatives are captured in [research.md](./research.md). Per-artifact contracts are in [contracts/](./contracts/).

## Technical Context

**Language/Version**: Python 3.10+ runtime constraint per `pyproject.toml`; the published Docker image pins `python:3.12-slim` per research §R1.
**Primary Dependencies**: FastMCP ≥3.0.0 (lifespan API + `--reload` watchfiles integration), Neo4j Python driver ≥5.28.0, sentence-transformers ≥5.1.0, pydantic-settings ≥2.11.0. No new Python dependencies are added by this spec.
**Storage**: Neo4j 2026.03.1 (CalVer) with vector index — schema unchanged from `001-baseline-rag`. Persistence via Docker named volume `neo4j_data` for the local power-user environment.
**Testing**: pytest + pytest-asyncio (already configured). New tests: `tests/test_mcp/test_lifespan.py` for import-side-effect-free behaviour, lifespan global population, `ensure_vector_index` invocation, and teardown.
**Target Platform**: Linux containers (multi-arch `linux/amd64` + `linux/arm64` for Apple Silicon). Local power-user host: Linux/macOS/Windows with Docker. Dev host: Linux VM running `uv` natively.
**Project Type**: Single project — no frontend/mobile components. Existing layered architecture preserved (MCP server / service / repository / provider).
**Performance Goals**: First MCP tool call within 5 s of compose `healthy` (SC-002). Time-to-running power-user setup < 5 min excluding image pull (SC-001).
**Constraints**: Loopback-only port binding for both Memento (`8000`) and Neo4j (`7687`, `7474`) per FR-005. Image MUST NOT reference `:latest` (FR-011). Module imports MUST NOT trigger Neo4j connections or model loads (SC-005). No backwards-compat shims for removed `Config.mcp_host` / `Config.mcp_port` per Constitution YAGNI.
**Scale/Scope**: Personal-scale, single-tenant. Release cadence is manual, low single-digit per month.

## Constitution Check

Evaluated against [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.1.0.

| Gate | Verdict | Notes |
|---|---|---|
| **I. YAGNI** | ✅ Pass | `Config.mcp_host` / `Config.mcp_port` deleted (FR-007) — no `Optional[str]` shim, no `removed_in_v0_2.py` ghost. No premature abstractions in the lifespan or Dockerfile. |
| **II. KISS** | ✅ Pass | Two GHA workflows, not a release-please framework. Single Dockerfile with two stages. Healthcheck via `curl`, not a custom Python health-probe. Lifespan keeps existing module-level `service` global so 16 existing tests do not need rewriting (research §R5 alternatives). |
| **III. Established Design Patterns** | ✅ Pass | No new patterns introduced. Factory/Repository/Interface Segregation/Plugin all preserved unchanged. |
| **IV. Layered Architecture** | ✅ Pass | Layer responsibilities unchanged. Lifespan composes layers in the existing order: Config → Provider (embedder) → Repository (Neo4j) → Service (Memory). |
| **V. Mandatory Testing (NON-NEGOTIABLE)** | ✅ Pass plan-time | Tasks phase will produce ordered tasks where every implementation task is blocked by its corresponding failing test (per Phase 2 template). Final gate is `uv run pytest` green. |
| **VI. TDD (Red → Green → Refactor)** | ✅ Pass plan-time | Per `data-model.md` test-surface delta and `contracts/server-lifespan.md` test plan: failing tests for `test_lifespan.py`, the `Config` `embedding_cache_dir` default, and the deletion of `mcp_host`/`mcp_port` are written before the corresponding implementation. Dockerfile / compose / GHA artifacts are infrastructure with no unit-test surface; their "test" is the manual + CI verification described in their contracts and in [quickstart.md](./quickstart.md). |

**Post-design re-check**: All Phase 1 artifacts (data-model.md, contracts/, quickstart.md) preserve the gate verdicts above. No new violations introduced.

**Quality Gates** (constitution §"Quality Gates"):
1. Code Gate (YAGNI/KISS) — green per above.
2. Pattern Gate — green; no patterns added or removed.
3. Architecture Gate — green; no cross-layer leaks.
4. TDD Gate — to be enforced during /speckit-tasks ordering.
5. Test Gate — to be enforced at end of implementation (`uv run pytest`).
6. Clean Code Gate — to be enforced via review; FR-007 explicitly removes dead code.

## Project Structure

### Documentation (this feature)

```text
specs/002-container-setup/
├── plan.md                           # This file
├── research.md                       # Phase 0 output (Decision/Rationale/Alternatives per unknown)
├── data-model.md                     # Phase 1: Container Image + Deployment Configuration entities; affected files; test delta
├── quickstart.md                     # Phase 1: power-user + dev flow walkthroughs; pass criteria per SC
├── contracts/
│   ├── dockerfile.md                 # Image build contract
│   ├── docker-compose.md             # Local power-user orchestration contract
│   ├── mcp-json.md                   # Dev-loop .mcp.json contract
│   ├── mcp-client-config.md          # README-published power-user client config blocks
│   ├── github-actions.md             # auto-tag.yml + publish.yml contracts
│   └── server-lifespan.md            # src/mcp/server.py refactor contract
├── research/
│   └── mcp-distribution-patterns.md  # Pre-spec exploration (carried forward)
├── checklists/
│   └── requirements.md               # Pre-existing spec quality checklist
├── spec.md                           # Authoritative spec
└── tasks.md                          # Phase 2 — produced by /speckit-tasks (NOT this command)
```

### Source Code (repository root)

```text
.
├── Dockerfile                        # NEW — multi-stage uv build, model baked, ENTRYPOINT fastmcp run
├── docker-compose.yml                # NEW — power-user orchestration, pinned ghcr image, healthchecks
├── .mcp.json                         # NEW — dev-loop config (Memento --reload + neo4j-cypher MCP)
├── .dockerignore                     # NEW — keeps .git/.venv/.cache/tests out of build context
├── .env.example                      # MODIFIED (verified — no removed-var refs to clean up)
├── .github/
│   └── workflows/
│       ├── auto-tag.yml              # NEW — main → tag from pyproject.toml [project] version
│       └── publish.yml               # NEW — tag → multi-arch GHCR push
├── pyproject.toml                    # MODIFIED — version bumped to 0.0.2 (release-initiation per FR-011)
├── README.md                         # MODIFIED — Power-User + Developer sections; native-HTTP + bridge config blocks
├── Documentation/
│   └── known-tech-debt.md            # MODIFIED — TD-003 resolved; TD-004 interim-resolution note
├── src/
│   ├── mcp/
│   │   └── server.py                 # MODIFIED — lifespan refactor; __main__ deleted
│   └── utils/
│       └── config.py                 # MODIFIED — drop mcp_host/mcp_port; default embedding_cache_dir=".cache/models"
├── tests/
│   └── test_mcp/
│       ├── conftest.py               # MODIFIED (verified) — autouse import patches kept as belt-and-suspenders
│       ├── test_server.py            # PRESERVED — 16 existing tests pass unchanged
│       └── test_lifespan.py          # NEW — import-side-effect-free, lifespan population, ensure_vector_index, teardown
└── .devcontainer/                    # DELETED — superseded by VM dev environment per ADR-007
```

**Structure Decision**: Single-project layout (existing `src/` + `tests/` retained). This feature is primarily packaging and infrastructure; no new layers or modules are introduced. The deltas listed above are the complete set.

## Complexity Tracking

> No Constitution Check violations.

The Constitution Check has zero violations. All five Core Principles + the Quality Gates are satisfied as written. There is no need to fill the Complexity Tracking table — every design choice is either trivially in line with YAGNI/KISS or explicitly justified in [research.md](./research.md) under its R-section (e.g. R5 explains why module-level globals are kept rather than migrating to FastMCP context dicts; R9 explains why we use single-job multi-arch via QEMU rather than splitting per-platform).
