# Tasks: 003-container-polish-devloop

**Input**: Design documents from `specs/003-container-polish-devloop/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/healthcheck.md ✓

**Tests**: Included — TDD is explicitly required by the plan for FR-002 and FR-012 (see plan.md Phase A).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Create the shared verification artifact used by both US1 and US2

- [X] T001 Create `specs/003-container-polish-devloop/verification.md` with skeleton sections: Power-User Verification (FR-007), Claude Code Dev Loop (FR-008), Gemini CLI Dev Loop (FR-008); leave body of each section as TBD placeholders

---

## Phase 2: Foundational (TDD — Write Tests First)

**Purpose**: Write failing tests for FR-002 and FR-012 before touching implementation code; gate all server.py changes behind a green baseline

**⚠️ CRITICAL**: Tests must be written and confirmed failing before any implementation in Phases 3–5

- [X] T002 [P] Write `test_lifespan_closes_driver_on_startup_failure` in `tests/test_mcp/test_lifespan.py`: monkeypatch `repository.ensure_vector_index` to raise `RuntimeError`; assert `repository.close` was called exactly once (covers FR-002)
- [X] T003 [P] Write `test_module_globals_only_service` in `tests/test_mcp/test_lifespan.py`: after lifespan exits, assert `service` is `None` at module scope and that `config`, `embedder`, `repository` are not present as module-level attributes on the server module (covers FR-012)
- [X] T004 Run `uv run pytest` and confirm T002 and T003 fail, all existing tests pass — baseline established

**Checkpoint**: Foundation ready — implementation phases can now begin

---

## Phase 3: User Story 1 — Power-User Setup Is Production-Ready (Priority: P1) 🎯 MVP

**Goal**: Container healthcheck reliably transitions to `healthy`, lifespan closes the Neo4j driver on startup failure, `.env.example` removes all shared-password guidance, and the Dockerfile grants write access to `/app` for the runtime user.

**Independent Test**: On a clean machine with Docker, `git clone … && cd memento && cp .env.example .env`, set a password, `docker compose up -d`, verify both services report `healthy` via `docker compose ps`, then exercise `remember`/`recall` via an MCP client. Confirm `.env.example` contains no specific password value and README does not suggest one.

### Implementation for User Story 1

- [X] T005 [US1] Add `@mcp.custom_route("/health", methods=["GET"])` returning `JSONResponse({"status": "ok"})` to `src/mcp/server.py`; add `from starlette.requests import Request` and `from starlette.responses import JSONResponse` imports (FR-001; see research.md §R1 for confirmed API shape)
- [X] T006 [US1] Fix lifespan driver-leak in `src/mcp/server.py`: move the `try` block to open immediately after `Neo4jRepository(...)` so `ensure_vector_index`, `MemoryService` construction, and the `yield` body are all inside `try/finally`; embedder construction stays before the driver and is not inside the `try` (FR-002; see research.md §R2 for correct shape)
- [X] T007 [P] [US1] Update `docker-compose.yml`: change the memento service `healthcheck.test` to `["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]`; bump the memento image tag from `v0.0.2` to `v0.0.3` (FR-001)
- [X] T008 [P] [US1] Rewrite the `MEMENTO_NEO4J_PASSWORD` block in `.env.example`: remove any specific password value or suggestion; keep only the 8-character minimum note and add `# Generate one: openssl rand -base64 12` hint (FR-004; see research.md §R6 for target shape)
- [X] T009 [P] [US1] Update `Dockerfile` runtime stage: add `--user-group` flag to the `useradd` command; move `RUN chown -R app:app /app` to after all `COPY --from=builder` instructions (FR-006; see research.md §R5 for correct Dockerfile shape)
- [X] T010 [P] [US1] Update `Documentation/known-tech-debt.md`: add a `Priority:` field (`high` or `low`) to existing entries TD-001–TD-004; append new entries for each deferred feedback item (H4, M3, M5, M6, L1–L6) following the existing TD-001 template style; M5 and M6 are `high`, all others are `low`; include `Remediation: N/A — advisory-only` for M6 (FR-009, FR-010; see research.md §R10 for full triage table)
- [X] T011 [P] [US1] Add embedder-reentrant invariant note to `specs/002-container-setup/contracts/server-lifespan.md`: one sentence stating the embedder is reentrant/resource-free; update the module-level exports list to reflect that only `service` remains at module scope after FR-012 (cross-spec contract update per plan.md Phase D)
- [X] T012 [US1] Run `uv run pytest`; confirm `test_lifespan_closes_driver_on_startup_failure` (T002) now passes and no existing tests regress (validates FR-002 implementation)

**Checkpoint**: US1 independently testable — container config, lifespan safety, env guidance, and filesystem permissions all complete

---

## Phase 4: User Story 2 — Dev Loop Is Validated End-to-End (Priority: P1)

**Goal**: Claude Code and Gemini CLI can connect to the memento MCP server via the project-level `.mcp.json`, observe tool description changes after `--reload` triggers a worker respawn, and confirm database state via `cypher-shell`.

**Independent Test**: With `docker compose up neo4j -d` running, launch an MCP client at the repo root with `.mcp.json` honoured; the `memento` server appears in the tool listing. Edit `src/mcp/server.py` and save; on the next tool call after worker respawn, the new description is visible. Run `remember` then `recall`; issue a `cypher-shell` query confirming a `Memory` node exists with the stored content.

### Implementation for User Story 2

- [X] T013 [US2] Add `Annotated[T, Field(description="...")]` parameter descriptions to `remember()` and `recall()` in `src/mcp/server.py`: `content` ("The text to store as a memory. Must be non-empty and at most 4000 characters."), `confidence` ("How confident you are in this memory, from 0.0 (uncertain) to 1.0 (certain). Values outside [0, 1] are rejected."), `query` ("The search query used to find semantically similar memories."), `limit` ("Maximum number of matching memories to return, ordered by relevance."); add `from typing import Annotated` and `from pydantic import Field` imports (FR-013; see research.md §R4 and data-model.md for exact description text)
- [X] T014 [P] [US2] Remove the `neo4j-cypher` server entry from `.mcp.json`, leaving only the `memento` server entry (FR-008; DB-state probes use `cypher-shell` directly per spec Clarifications §"Dev-loop validation")
- [ ] T015 [US2] Exercise the Claude Code dev loop end-to-end: (1) `docker compose up neo4j -d`, (2) launch Claude Code at the repo root honouring `.mcp.json`, (3) verify T013's parameter descriptions appear in the memento tool listing on the next call after the `--reload` worker respawn, (4) run `remember`/`recall` cycle, (5) run `cypher-shell -u neo4j -p $MEMENTO_NEO4J_PASSWORD --database neo4j 'MATCH (m:Memory) RETURN m.content LIMIT 5'` against the Neo4j container and confirm the `Memory` node exists; document canonical prompt, canonical `cypher-shell` query, and Claude Code transcript in `specs/003-container-polish-devloop/verification.md` (FR-008)
- [ ] T016 [US2] Repeat the dev loop validation with Gemini CLI using the same flow as T015; document Gemini CLI transcript and any client-specific caveats (e.g., subprocess respawn behaviour, session-level tool-description caching) in `specs/003-container-polish-devloop/verification.md` (FR-008)

**Checkpoint**: US2 independently testable — dev loop validated on both clients, transcripts and cypher-shell results documented in verification.md

---

## Phase 5: User Story 3 — Repository Hygiene Cleanup (Priority: P3)

**Goal**: `AGENTS.md` uses `.specify/feature.json` for feature-path discovery instead of a hardcoded path; `src/mcp/server.py` has only `service` at module scope; `README.md` Developer Setup section covers the complete onboarding flow.

**Independent Test**: Search the repo for the previously hardcoded feature directory path and confirm it is absent from `AGENTS.md`. Confirm `config`, `embedder`, and `repository` are not module-level names in `src/mcp/server.py`. Confirm `service: MemoryService | None = None` annotation is present at module scope.

### Implementation for User Story 3

- [X] T017 [P] [US3] Update `AGENTS.md`: replace the hardcoded `<!-- SPECKIT START -->` block content with the path-discovery phrasing from research.md §R7 (instructs the agent to read `.specify/feature.json` `feature_directory` key, then read `<feature_directory>/plan.md`); leave `CLAUDE.md` and `GEMINI.md` as `@AGENTS.md` delegates (FR-011)
- [X] T018 [US3] Refactor `src/mcp/server.py` module globals: remove `config`, `embedder`, and `repository` module-level declarations; move their initialization into `lifespan()` as local variables; add `service: MemoryService | None = None` annotation at module scope replacing the bare `service = None` (FR-012; see research.md §R3 and data-model.md for the exact scope table)
- [X] T019 [P] [US3] Update `README.md` Developer Setup section with: (a) launching ritual for Claude Code (`set -a; source .env; set +a` or `direnv allow`) and Gemini CLI, (b) troubleshooting note for stale `neo4j_data` volume after a password change (`docker compose down -v`), (c) Python version note deferring to `pyproject.toml`'s `requires-python` instead of hardcoding a version, (d) Bolt-port reachability note (from spec Clarifications §"Other items rolled in"); (e) confirm README contains no specific `MEMENTO_NEO4J_PASSWORD` example value — remove any such value if found (SC-006)
- [X] T020 [US3] Run `uv run pytest`; confirm `test_module_globals_only_service` (T003) now passes and no existing tests regress (validates FR-012 implementation)

**Checkpoint**: US3 independently testable — no hardcoded paths in AGENTS.md, only `service` at module scope, README complete

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Build and publish the v0.0.3 image; complete power-user end-to-end verification against the locally-built and published images

- [ ] T021 Build the `v0.0.3` Docker image locally (`docker build -t ghcr.io/rigrergl/memento:v0.0.3 .`) and run the power-user end-to-end verification against the locally-built image: `docker compose up -d` → both services `healthy` → `remember`/`recall` via an MCP client; document results in the Power-User Verification section of `specs/003-container-polish-devloop/verification.md` (FR-007)
- [ ] T022 Publish the `v0.0.3` image to GHCR (`docker push ghcr.io/rigrergl/memento:v0.0.3`); update `docker-compose.yml` if the image digest needs pinning; verify `docker compose pull && docker compose up -d` against the published image produces both services `healthy` (FR-007 — published-image verification)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user story implementation
- **US1 (Phase 3)**: Depends on Phase 2 (tests written) — can start after T004
- **US2 (Phase 4)**: Depends on Phase 2; T013 must follow T006 (both in server.py — apply sequentially to avoid conflicts)
- **US3 (Phase 5)**: Depends on Phase 2; T018 must follow T006 and T013 (all in server.py)
- **Polish (Phase 6)**: Depends on US1, US2, US3 all complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — independent of US2 and US3 except server.py sequencing
- **US2 (P1)**: After Phase 2; T013 depends on T006 (server.py ordering)
- **US3 (P3)**: After Phase 2; T018 depends on T006 and T013 (server.py ordering)

### Within Each Phase

- All `[P]`-marked tasks can run in parallel (they touch different files)
- server.py tasks must be applied sequentially: T005 → T006 → T013 → T018
- Pytest validation tasks (T004, T012, T020) must run after all implementation tasks in their phase

---

## Parallel Execution Examples

### Phase 2 (Foundational)

```
Parallel: T002 (test_lifespan_closes_driver_on_startup_failure)
          T003 (test_module_globals_only_service)
Sequential: T004 (run pytest baseline check)
```

### Phase 3 (US1) — after T004

```
Sequential: T005 → T006 (server.py — apply in order)
Parallel:   T007 (docker-compose.yml)
            T008 (.env.example)
            T009 (Dockerfile)
            T010 (known-tech-debt.md)
            T011 (server-lifespan.md contract)
Sequential: T012 (pytest validation — after T006)
```

### Phase 4 (US2) — after T006

```
Sequential: T013 (server.py — after T006)
Parallel:   T014 (.mcp.json — after T013 is not required, different file)
Sequential: T015 → T016 (dev loop exercises — sequential, different clients)
```

### Phase 5 (US3) — after T013

```
Sequential: T018 (server.py — after T006 and T013)
Parallel:   T017 (AGENTS.md)
            T019 (README.md)
Sequential: T020 (pytest validation — after T018)
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: US1
4. **STOP and VALIDATE**: `docker compose up -d` → both services `healthy`
5. US1 ships the power-user fixes and is independently demo-able

### Incremental Delivery

1. Setup + Foundational → baseline
2. US1 → container polish complete → locally demo-able
3. US2 → dev loop validated on both clients
4. US3 → hygiene complete
5. Polish → v0.0.3 published

---

## Notes

- `[P]` tasks touch different files and have no dependencies on incomplete tasks — safe to parallelize
- server.py tasks (T005, T006, T013, T018) must be applied in that order — all modify the same file
- T015 and T016 require a live Neo4j container (`docker compose up neo4j -d`) and are human/agent-executed verification tasks, not automated tests
- T022 (docker push) pushes to GHCR — confirm with maintainer before executing
- Existing tests in `tests/test_mcp/test_server.py` and `tests/test_mcp/test_lifespan.py` must continue passing at every pytest checkpoint (T004, T012, T020)
