---
description: "Tasks for 002-container-setup"
---

# Tasks: 002-container-setup (Container Setup for Local Power Users + Dev Loop)

**Input**: Design documents from `/specs/002-container-setup/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required per Constitution Principles V (Mandatory Testing) and VI (TDD). Unit tests precede implementation for `src/utils/config.py` and `src/mcp/server.py`. Infrastructure artifacts (Dockerfile, docker-compose.yml, .mcp.json, GHA workflows) have no unit-test surface; their verification is the manual + CI checks captured in [quickstart.md](./quickstart.md) and the Polish phase.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. Both user stories are P1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- File paths are absolute or repo-root-relative as appropriate.

## Path Conventions

Single-project layout (existing `src/` + `tests/`). New artifacts at repo root: `Dockerfile`, `docker-compose.yml`, `.mcp.json`, `.dockerignore`, `.github/workflows/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization for the release-tagging mechanism and build context hygiene that the rest of the work depends on.

- [X] T001 Bump `[project] version` from `0.0.1` to `0.0.2` in `pyproject.toml` (release-initiation per FR-011 §Version sync policy and R13)
- [X] T002 [P] Create `/home/grey/source/memento/.dockerignore` excluding `.git`, `.venv`, `.cache`, `tests/`, `specs/`, `Documentation/`, `.devcontainer/`, `.github/`, `*.md`, `__pycache__/` (R1 build context hygiene)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Server lifespan refactor and `Config` cleanup that BOTH user stories depend on. US1 (compose) cannot run the published image without these; US2 (dev loop) cannot launch via `.mcp.json --reload` without them either.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests (write FIRST, must FAIL before implementation) ⚠️

- [X] T003 [P] Add failing test in `tests/test_utils/test_config.py` that constructs `Config()` with all required env vars except `MEMENTO_EMBEDDING_CACHE_DIR` and asserts `config.embedding_cache_dir == ".cache/models"` (FR-003, R3)
- [X] T004 [P] Add failing test in `tests/test_utils/test_config.py` asserting `Config` has no attribute `mcp_host` and no attribute `mcp_port` (FR-007, R6)
- [X] T005 [P] Create `tests/test_mcp/test_lifespan.py` with failing test `test_bare_import_does_not_construct_config_or_repository_or_embedder`: patches `src.utils.config.Config.__init__`, `src.graph.neo4j.Neo4jRepository.__init__`, and `src.embeddings.local_embedding_provider.SentenceTransformer` to raise `AssertionError("import touched it")`, then `import src.mcp.server`; import MUST succeed (SC-005, contracts/server-lifespan.md §Test plan #1)
- [X] T006 [P] Add failing test `test_lifespan_populates_module_globals` in `tests/test_mcp/test_lifespan.py`: enters `mcp.lifespan(mcp)` async context, asserts module-level `config`, `embedder`, `repository`, `service` are non-None after `__aenter__` (contracts/server-lifespan.md §Test plan #2)
- [X] T007 [P] Add failing test `test_lifespan_calls_ensure_vector_index_once` in `tests/test_mcp/test_lifespan.py`: patches `Neo4jRepository.ensure_vector_index`, runs lifespan `__aenter__`, asserts called exactly once (FR-006c, contracts/server-lifespan.md §Test plan #3)
- [X] T008 [P] Add failing test `test_lifespan_aexit_closes_repository` in `tests/test_mcp/test_lifespan.py`: enters and exits lifespan, asserts `repository.close` was awaited (contracts/server-lifespan.md §Test plan #4)

### Implementation (in dependency order)

- [X] T009 Edit `src/utils/config.py`: delete `mcp_host` and `mcp_port` fields; add `default=".cache/models"` to `embedding_cache_dir` Field; update class docstring example (FR-003, FR-007, R3, R6) — makes T003, T004 pass
- [X] T010 Add `close(self) -> None` method to `Neo4jRepository` in `src/graph/neo4j.py` that calls `self._driver.close()` if it has not yet been closed (idempotent); cited as required by contracts/server-lifespan.md §Required behaviour `__aexit__`
- [X] T011 Refactor `src/mcp/server.py` per contracts/server-lifespan.md: delete the `if __name__ == "__main__":` block; introduce module-level placeholders `config: Config | None = None`, `embedder = None`, `repository: Neo4jRepository | None = None`, `service: MemoryService | None = None`; define `@asynccontextmanager async def lifespan(_mcp)` populating these globals in the order Config → embedder → repository → `await asyncio.to_thread(repository.ensure_vector_index)` → service, with `yield` and `finally: await asyncio.to_thread(repository.close)`; pass `lifespan=lifespan` to `FastMCP("Memento", lifespan=lifespan)`; keep `remember`/`recall` tool bodies referencing the module-level `service` (FR-006, R5) — makes T005, T006, T007, T008 pass
- [X] T012 Verify `tests/test_mcp/conftest.py` autouse `patch_server_imports` fixture still functions after the refactor (it becomes belt-and-suspenders, no-op at import time but kept for regression protection per contracts/server-lifespan.md §Migration notes); leave the comment in place explaining why

**Checkpoint**: `uv run pytest` is green; `python -c "import src.mcp.server"` does not open a Neo4j connection or load a model. Foundation ready — both user stories can now begin in parallel.

---

## Phase 3: User Story 1 — Power User Local Setup (Priority: P1) 🎯 MVP

**Goal**: A user with only Docker installed can `git clone` and `docker compose up -d` to get a healthy Memento HTTP daemon, wire any MCP client to `http://localhost:8000/mcp/`, and exercise `remember`/`recall` end-to-end. The image is pulled from `ghcr.io` by pinned semver tag.

**Independent Test**: Run [quickstart.md Flow 1](./quickstart.md#flow-1--power-user-us1) on a clean machine after the bootstrap window has closed; SC-001 through SC-004 must pass.

### Implementation for User Story 1

#### Container image

- [X] T013 [US1] Create `/home/grey/source/memento/Dockerfile` per contracts/dockerfile.md and research §R1, §R3, §R14: builder stage on `python:3.12-slim` installs `uv`, copies `pyproject.toml` + `uv.lock`, runs `uv sync --frozen --no-install-project --no-dev`, copies `src/`, then bakes the model with `RUN .venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', cache_folder='/app/.cache/models')"`; runtime stage on `python:3.12-slim` `apt-get install -y --no-install-recommends curl ca-certificates`, creates non-root `app` user, `COPY --from=builder` for `/app/.venv`, `/app/src`, `/app/.cache/models`, `/app/pyproject.toml`, sets `ENV PATH=/app/.venv/bin:$PATH`, `WORKDIR /app`, `USER app`, `ENTRYPOINT ["fastmcp", "run", "src/mcp/server.py"]`, `CMD []` (FR-001, FR-002, FR-003)

#### Local power-user orchestration

- [X] T014 [US1] Create `/home/grey/source/memento/docker-compose.yml` per contracts/docker-compose.md and research §R4: `memento` service references `image: ghcr.io/rigrergl/memento:v0.0.2` (no `build:`, no `:latest`), `depends_on.neo4j.condition: service_healthy`, `command: ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]`, `ports: ["127.0.0.1:8000:8000"]`, environment block with `MEMENTO_NEO4J_URI=bolt://neo4j:7687`, `MEMENTO_NEO4J_USER=neo4j`, `MEMENTO_NEO4J_PASSWORD=${MEMENTO_NEO4J_PASSWORD:?...}` (required, no fallback default — compose fails at config-time when unset), `MEMENTO_EMBEDDING_PROVIDER=local`, `MEMENTO_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2` (NO `MEMENTO_EMBEDDING_CACHE_DIR`), and healthcheck `["CMD-SHELL", "curl -f http://localhost:8000/mcp/ || exit 1"]` (interval 10s, timeout 5s, retries 6, start_period 30s); `neo4j` service uses `image: neo4j:2026.03.1`, ports bound to `127.0.0.1`, `NEO4J_AUTH: neo4j/${MEMENTO_NEO4J_PASSWORD:?...}` (same enforcement), the Neo4j healthcheck and `volumes: ["neo4j_data:/data"]`; declare top-level `volumes: { neo4j_data: }` (FR-004, FR-005, FR-011)
- [ ] T015 [P] [US1] Run `docker compose config` against the new file and confirm it resolves with no warnings; capture the resolved YAML in the PR description as the validation artifact for contracts/docker-compose.md §Test plan

#### GitHub Actions release pipeline

- [X] T016 [P] [US1] Create `/home/grey/source/memento/.github/workflows/auto-tag.yml` per contracts/github-actions.md §Workflow 1 and research §R10: `on: push: branches: [main]`, `permissions: contents: write`, concurrency `auto-tag-${{ github.ref }}` with `cancel-in-progress: false`; steps `actions/checkout@v5` with `fetch-depth: 0`, read version via `VERSION=$(grep -E '^version = ' pyproject.toml | head -1 | sed -E 's/.*"(.*)"/\1/')`, exit early if `git rev-parse "v$VERSION"` succeeds, configure git as `github-actions[bot]` with email `41898282+github-actions[bot]@users.noreply.github.com`, `git tag -a "v$VERSION" -m "Release v$VERSION"`, `git push origin "v$VERSION"` (FR-011 §Auto-tagging)
- [X] T017 [P] [US1] Create `/home/grey/source/memento/.github/workflows/publish.yml` per contracts/github-actions.md §Workflow 2 and research §R9: `on: push: tags: ["v*.*.*"]`, `permissions: contents: read, packages: write`, concurrency `publish-${{ github.ref }}` with `cancel-in-progress: false`; steps `actions/checkout@v5`, `docker/setup-qemu-action@v3`, `docker/setup-buildx-action@v3`, `docker/login-action@v3` (registry `ghcr.io`, username `${{ github.actor }}`, password `${{ secrets.GITHUB_TOKEN }}`), `docker/metadata-action@v5` (id `meta`, `images: ghcr.io/rigrergl/memento`, tags `type=semver,pattern={{version}}` and `type=ref,event=tag`, NO `latest`), `docker/build-push-action@v6` (context `.`, `platforms: linux/amd64,linux/arm64`, `push: true`, `tags: ${{ steps.meta.outputs.tags }}`, `labels: ${{ steps.meta.outputs.labels }}`, `cache-from: type=gha`, `cache-to: type=gha,mode=max`) (FR-011 §Multi-arch)

#### Tech-debt ledger

- [X] T018 [P] [US1] Edit `Documentation/known-tech-debt.md`: change TD-003 Status to "Resolved by ADR-007 / spec 002-container-setup — `Config.mcp_host` and `Config.mcp_port` deleted; transport/host/port now CLI flags; local power-user compose binds `127.0.0.1:8000`"; under TD-004 add a "Status update (2026-04-27)" subsection noting that 002-container-setup chose option 1 (bake into image) as the interim resolution and the longer-term volume-vs-hosted-API decision remains open (FR-008, R16)

#### README — Power-User section

- [X] T019 [US1] Restructure `README.md` per contracts/mcp-client-config.md and research §R15: add a top-level "Power-User Setup" section ahead of the existing Quick Start covering `git clone https://github.com/rigrergl/memento.git`, `cd memento`, `docker compose up -d`, then three MCP-client config blocks in order — Block 1 native HTTP `{"type": "http", "url": "http://localhost:8000/mcp/"}` marked as the recommended path for Claude Code/modern clients, Block 2 `npx -y mcp-remote http://localhost:8000/mcp/`, Block 3 `uvx mcp-proxy http://localhost:8000/mcp/`, both flagged as third-party bridges not maintained by this project; add an Upgrade subsection documenting `git pull && docker compose pull && docker compose up -d`; add a Bootstrap-window callout per FR-011 §Bootstrap warning that `docker compose pull` fails until the maintainer cuts the first tag and sets GHCR visibility to Public; remove every `python -m src.mcp.server` reference (the entrypoint no longer exists per FR-006) (FR-012, FR-013, R15)

**Checkpoint**: All US1 artifacts exist. After the bootstrap window described in FR-011 §Bootstrap closes, the [quickstart.md Flow 1](./quickstart.md#flow-1--power-user-us1) end-to-end run from a clean machine should pass SC-001 through SC-004. US1 is independently demonstrable.

---

## Phase 4: User Story 2 — Developer Dev Loop (Priority: P1)

**Goal**: A developer cloning the repo can `cp .env.example .env`, `docker compose up neo4j`, launch their MCP client in the repo, and have both Memento (with `--reload`) and `mcp-neo4j-cypher` MCP servers connected for self-validation, with edits to tools picked up on the next call after the client respawns the subprocess.

**Independent Test**: Run [quickstart.md Flow 2](./quickstart.md#flow-2--developer-us2); FR-006, FR-007, FR-009, FR-010, SC-005 must pass. The `test_lifespan.py` SC-005 assertion already covers import-side-effect-freedom in the test suite.

### Implementation for User Story 2

- [X] T020 [P] [US2] Create `/home/grey/source/memento/.mcp.json` per contracts/mcp-json.md and research §R7 with two `mcpServers`: `memento` → `command: "uv"`, `args: ["run", "fastmcp", "run", "src/mcp/server.py", "--reload"]`; `neo4j-cypher` → `command: "uvx"`, `args: ["mcp-neo4j-cypher"]`, `env: {"NEO4J_URI": "${MEMENTO_NEO4J_URI}", "NEO4J_USERNAME": "${MEMENTO_NEO4J_USER}", "NEO4J_PASSWORD": "${MEMENTO_NEO4J_PASSWORD}"}`; no literal credentials, no HTTP transport, no removed env vars (FR-009)
- [X] T021 [P] [US2] Verify `/home/grey/source/memento/.env.example` matches research §R8 final shape (Neo4j URI/user/password, embedding provider/model/cache_dir, max memory length) — already aligned; if any drift exists, correct in this task. No removed-var references should appear (FR-007, FR-010, R8)
- [X] T022 [US2] Add a "Developer Setup" section to `README.md` (after the Power-User Setup added in T019) covering `uv sync`, `cp .env.example .env`, `docker compose up neo4j -d`, `set -a; source .env; set +a`, and "open Claude Code or Gemini CLI from the repo root" — explaining `.mcp.json` wires both `memento` (`--reload`) and `neo4j-cypher`; cross-link to the existing `Documentation/` table-of-contents (R15)
- [X] T023 [P] [US2] Delete the `/home/grey/source/memento/.devcontainer/` directory (`devcontainer.json`, `Dockerfile`, `init-firewall.sh`, `start-inspector.sh`) — superseded by VM dev environment per ADR-007 (R15 cleanup)
- [X] T024 [P] [US2] Remove any dev-container references from `README.md` left over after T019/T022 (e.g. "Reopen in Container" / port-forwarding sections) (R15 cleanup)

**Checkpoint**: `.mcp.json` parses, both MCP servers connect from a launched Claude Code/Gemini CLI in the repo, editing `src/mcp/server.py` triggers a worker restart visible to the next tool call. US2 is independently demonstrable.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final verification gates per the Constitution and the post-merge bootstrap sequence.

- [X] T025 Run `uv run pytest` and confirm green — Quality Gate 5 (Test Gate). All 16 existing tests in `tests/test_mcp/test_server.py` plus the new lifespan and Config tests must pass
- [X] T026 [P] Run `uv run pytest --cov=src --cov-report=term-missing` and confirm `src/mcp/server.py` lifespan paths are exercised (per quickstart.md "Test-suite gate")
- [ ] T027 [P] Build the image locally: `docker build -t memento:test .` succeeds end-to-end on a fresh build cache; image size noted in PR description (target ≤ 500 MB compressed per contracts/dockerfile.md)
- [ ] T028 [P] Multi-arch build smoke: `docker buildx build --platform linux/amd64,linux/arm64 -t memento:test .` (no push) succeeds (contracts/dockerfile.md §Test plan)
- [ ] T029 [P] Offline embedding check: `docker run --rm --network none --entrypoint .venv/bin/python memento:test -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', cache_folder='/app/.cache/models')"` exits 0 — verifies SC-003 / FR-003
- [ ] T030 [P] Healthcheck binary present: `docker run --rm --entrypoint curl memento:test --version` prints curl's version (contracts/dockerfile.md §Test plan)
- [ ] T031 [P] Non-root verification: `docker run --rm --entrypoint id memento:test` reports a non-zero UID (contracts/dockerfile.md §Test plan)
- [ ] T032 Run [quickstart.md Flow 1](./quickstart.md#flow-1--power-user-us1) end-to-end against a locally-built image (substitute `image: memento:test` temporarily in a private branch of `docker-compose.yml` for pre-publish verification). Confirm SC-001, SC-002, SC-004 and the persistence/upgrade subflows
- [ ] T033 Run [quickstart.md Flow 2](./quickstart.md#flow-2--developer-us2) end-to-end. Confirm FR-009, FR-010, US2 acceptance scenarios 1 and 2
- [ ] T034 Document the post-merge bootstrap steps in the PR description per FR-011 §Bootstrap and contracts/github-actions.md §Joint test: (1) merge → `auto-tag.yml` creates `v0.0.2`, (2) tag push → `publish.yml` builds and pushes `ghcr.io/rigrergl/memento:0.0.2` and `:v0.0.2`, (3) maintainer sets package visibility to Public at `https://github.com/users/rigrergl/packages/container/memento/settings`, (4) clean-machine `git clone && docker compose up -d` validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup. **Blocks all user stories** (server.py + Config refactor are required by both US1 and US2).
- **User Story 1 (Phase 3, P1)**: Depends on Phase 2 completion only.
- **User Story 2 (Phase 4, P1)**: Depends on Phase 2 completion only.
- **Polish (Phase 5)**: Depends on US1 + US2 completion. T025 depends on every implementation task; T032 depends on T013–T019; T033 depends on T020–T024.

### Within Phase 2 (Foundational)

- T003, T004, T005, T006, T007, T008 (failing tests) before T009, T010, T011 (implementation) — TDD Red→Green per Constitution Principle VI.
- T009 (Config) is independent of T010 (Neo4jRepository.close) and can run in parallel with it.
- T011 (server.py refactor) depends on both T009 (Config) and T010 (`repository.close`).
- T012 verifies T011 did not break the existing conftest contract.

### Within Phase 3 (US1)

- T013 (Dockerfile) is independent of T014 (compose), T016/T017 (GHA), T018 (tech-debt), T019 (README).
- T015 (`docker compose config` validation) depends on T014.
- T019 (README Power-User section) is independent of the artifact tasks but should land in the same PR for coherence.

### Within Phase 4 (US2)

- T020 (`.mcp.json`), T021 (`.env.example` verification), T023 (`.devcontainer/` deletion) are independent and parallel.
- T022 (README Developer section) depends on T019 (README Power-User section) only because they edit the same file.
- T024 (remove leftover dev-container references) depends on T019 + T022.

### User Story Independence

US1 and US2 are independent after Phase 2: a developer can implement and verify either in isolation. US1 ships the published image + power-user compose; US2 ships the dev-loop `.mcp.json` + README dev section. Each is independently testable per its quickstart flow.

---

## Parallel Execution Examples

### Phase 2 — failing tests up front

```bash
# T003, T004, T005, T006, T007, T008 can be authored in parallel:
Task: "Add failing test for embedding_cache_dir default in tests/test_utils/test_config.py"
Task: "Add failing test for absence of mcp_host/mcp_port in tests/test_utils/test_config.py"
Task: "Create tests/test_mcp/test_lifespan.py with test_bare_import_does_not_construct_*"
Task: "Add test_lifespan_populates_module_globals to tests/test_mcp/test_lifespan.py"
Task: "Add test_lifespan_calls_ensure_vector_index_once to tests/test_mcp/test_lifespan.py"
Task: "Add test_lifespan_aexit_closes_repository to tests/test_mcp/test_lifespan.py"

# T009 and T010 can run in parallel after the failing tests are committed:
Task: "Edit src/utils/config.py — drop mcp_host/mcp_port; add .cache/models default"
Task: "Add Neo4jRepository.close() in src/graph/neo4j.py"
```

### Phase 3 — US1 artifact tasks fan out

```bash
# After Phase 2 closes, these run in parallel:
Task: "Create Dockerfile per contracts/dockerfile.md"
Task: "Create .github/workflows/auto-tag.yml per contracts/github-actions.md"
Task: "Create .github/workflows/publish.yml per contracts/github-actions.md"
Task: "Update Documentation/known-tech-debt.md TD-003/TD-004"
```

### Phase 5 — image verification fan-out

```bash
# After T013 completes, these run in parallel:
Task: "docker buildx build --platform linux/amd64,linux/arm64 -t memento:test ."
Task: "docker run --rm --network none --entrypoint .venv/bin/python memento:test -c '...'"
Task: "docker run --rm --entrypoint curl memento:test --version"
Task: "docker run --rm --entrypoint id memento:test"
```

---

## Implementation Strategy

### MVP First (US1 only)

US1 is the externally-visible MVP — it is what new users encounter on `git clone`.

1. Phase 1 Setup (T001–T002).
2. Phase 2 Foundational (T003–T012).
3. Phase 3 US1 (T013–T019).
4. Run [quickstart.md Flow 1](./quickstart.md#flow-1--power-user-us1) against a locally-built image (T032 from Polish, pulled forward).
5. Stop, validate, deploy/demo via the bootstrap sequence (T034).

### Incremental Delivery

Both stories are P1 and small, so the natural delivery is a single PR landing US1 + US2 together. If bisection becomes necessary:

1. Phase 1 + Phase 2 → land alone behind a fence; not user-visible (server still runs via `fastmcp run` driven by tests).
2. + Phase 3 → power-user setup live (after the bootstrap window).
3. + Phase 4 → dev loop live.

### Parallel Team Strategy

After Phase 2 closes, two developers can split:

- Developer A: Phase 3 US1 (Dockerfile + compose + GHA + tech-debt + README Power-User).
- Developer B: Phase 4 US2 (`.mcp.json`, README Developer, devcontainer cleanup).

They reconverge in Phase 5 (shared `uv run pytest` + quickstart runs).

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in the same phase.
- [US1]/[US2] labels map each task to its user-story phase for traceability and independent delivery.
- TDD ordering inside Phase 2 is mandatory per Constitution Principle VI: T003–T008 must be red before T009–T011 turn them green.
- Infrastructure tasks (Dockerfile, compose, `.mcp.json`, GHA) are verified by the Phase 5 manual checks plus the post-merge bootstrap sequence — they have no unit tests by design (per plan.md Constitution Check, gate VI).
- Commit after each task or coherent group; the natural grouping is one commit per phase or per [P]-cluster.
- The bootstrap window described in FR-011 leaves `main` transiently broken (~10–15 min). T034 keeps that window short and explicit.
- Task counts: Phase 1 = 2, Phase 2 = 10 (6 tests + 4 impl), Phase 3 (US1) = 7, Phase 4 (US2) = 5, Phase 5 (Polish) = 10. Total = 34.
