# Feature Specification: 002-container-setup

**Feature Branch**: `002-container-setup`  
**Created**: 2026-04-20
**Status**: Draft  
**Input**: User description: "Implement decisions described in ADR-007. Bake embeddings into image for now. Code refactoring (lifespan hooks) included. Dev-loop autonomous iteration deferred to a separate spec. Cloud Run deployment deferred to a separate spec."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Power User Local Setup (Priority: P1)

As a technical user, I want to run Memento locally without managing Python/Neo4j installations, so I can add memory capabilities to my LLM with minimal setup.

**Why this priority**: This is the core "Local" deployment target defined in ADR-007.

**Independent Test**: `git clone` the Memento repo, run `docker compose up -d`, add an MCP entry pointing at `http://localhost:8000/mcp/` to an MCP client config (native HTTP for clients that support it; an `mcp-remote` or `mcp-proxy` bridge as a fallback for stdio-only clients), launch the client, and verify `remember`/`recall` work end-to-end. No manual build; image is pulled from `ghcr.io` via the pinned tag in the committed `docker-compose.yml`.

**Acceptance Scenarios**:

1. **Given** a machine with Docker installed, **When** I `git clone` the Memento repo and run `docker compose up -d`, **Then** Docker pulls the pinned Memento image from `ghcr.io`, starts Neo4j, waits for its healthcheck, and exposes Memento's HTTP MCP endpoint on `127.0.0.1:8000`.
2. **Given** Memento is running as a daemon, **When** I add an MCP entry pointing at `http://localhost:8000/mcp/` to my client config — native HTTP (`{"type": "http", "url": "..."}`) for clients that support it, or a bridge (`npx mcp-remote …` / `uvx mcp-proxy …`) for stdio-only clients — and launch the client, **Then** the client connects successfully and the `remember` and `recall` tools are callable.
3. **Given** the stack is already running, **When** my MCP client disconnects and reconnects (or a new client attaches), **Then** the daemon serves the new connection immediately — no per-spawn cold start — and Neo4j data persists via the named volume.
4. **Given** a new release has bumped the pinned image tag in `docker-compose.yml` on `main`, **When** I run `git pull && docker compose pull && docker compose up -d`, **Then** the upgraded image is pulled and started; no silent upgrade occurs without the `git pull` step.

---

### User Story 2 - Developer Dev Loop (Priority: P1)

As a developer working on Memento, I want to run the MCP server directly in my VM with reload-on-change and a Neo4j MCP server pre-wired for self-validation, so I can iterate on tools and verify DB mutations without extra setup.

**Why this priority**: Shares the `server.py` refactor and compose artifacts with US1, and is the path by which every subsequent feature is implemented and tested.

**Independent Test**: Clone the repo, copy `.env.example` to `.env`, run `docker compose up neo4j`, launch an MCP client that reads `.mcp.json` — both Memento and Neo4j MCP servers are available; editing a tool causes the next tool call (after the client respawns the subprocess) to exercise the new code.

**Acceptance Scenarios**:

1. **Given** a fresh clone with `.env` copied from `.env.example` and no values edited, **When** I run `docker compose up neo4j` and launch my MCP client in the repo, **Then** the client reads `.mcp.json`, spawns Memento via `uv run fastmcp run src/mcp/server.py --reload`, and connects to the Neo4j MCP server with credentials interpolated from the same env vars.
2. **Given** the dev server is running under `--reload`, **When** I edit a tool in `src/mcp/server.py`, **Then** `fastmcp` restarts the worker, the current MCP subprocess drops, and the client respawns it on the next tool call — exercising the new code with at most one failed call visible to the agent.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a multi-stage Dockerfile that produces a slim production image using `uv`.
- **FR-002**: The Dockerfile MUST declare `ENTRYPOINT ["fastmcp", "run", "src/mcp/server.py"]` with an empty `CMD`, so per-environment CLI flags (transport, host, port) are supplied by compose `command:` or Cloud Run `args` without repeating the entrypoint.
- **FR-003**: System MUST bake the default embedding model (`sentence-transformers/all-MiniLM-L6-v2`) into the Docker image to ensure fast cold starts and offline capability. The model MUST be baked to a path that the running server resolves without requiring per-environment override of `MEMENTO_EMBEDDING_CACHE_DIR` — i.e. `Config.embedding_cache_dir` gains a sensible default (e.g. `.cache/models` resolved relative to the container's `WORKDIR`) and the Dockerfile bakes the model to that same path. Dev (`.env`) keeps its existing value; compose does not need to set the var.
- **FR-004**: System MUST provide a `docker-compose.yml` committed to the repo root for local power users that references the published ghcr.io Memento image by **pinned semver tag** (no `build:` directive, no `:latest`), orchestrates Memento and Neo4j, waits for Neo4j's healthcheck before Memento starts, persists Neo4j data via a named volume, starts Memento as a long-lived HTTP daemon via `command: ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]`, and includes a healthcheck for the Memento service (`test: ["CMD-SHELL", "curl -f http://localhost:8000/mcp/ || exit 1"]`) so `docker compose ps` reflects actual HTTP readiness. Distribution is via `git clone`; users do not download the compose file separately.
- **FR-005**: The `docker-compose.yml` MUST bind both Memento's HTTP port (`127.0.0.1:8000:8000`) and Neo4j's host ports (`127.0.0.1:7687:7687`, `127.0.0.1:7474:7474`) to `127.0.0.1` rather than Docker's default `0.0.0.0`, so neither service is exposed on shared networks.
- **FR-006**: System MUST refactor `src/mcp/server.py` per ADR-007:
  - Delete the `if __name__ == "__main__":` block and the transport/host/port imports that only existed to serve it.
  - Move expensive resource construction (`Config`, embedder, `Neo4jRepository`, `MemoryService`) into a FastMCP lifespan hook so bare imports do not trigger Neo4j connections or model loads.
  - Move `repository.ensure_vector_index()` into the same lifespan hook (wrapped with `asyncio.to_thread` or made async), fixing the latent bug where `fastmcp run` currently skips index creation.
- **FR-007**: System MUST remove `MEMENTO_TRANSPORT`, `MEMENTO_MCP_HOST`, and `MEMENTO_MCP_PORT` environment variables and the corresponding `Config.mcp_host` / `Config.mcp_port` fields, delegating transport/host/port to CLI flags passed to `fastmcp run`. This resolves TD-003.
- **FR-008**: System MUST update `Documentation/known-tech-debt.md`:
  - **TD-004**: record that FR-003 (baking the model into the image) is this spec's interim resolution for the power-user distribution path, while leaving the longer-term volume-vs-hosted-API decision open.
  - **TD-003**: refresh the historical-risk and status wording to reflect that the local power-user setup now uses HTTP bound to `127.0.0.1` via compose port-binding (not stdio), and that the dev loop is the only stdio path.
- **FR-009**: System MUST include a `.mcp.json` at the project root for local development, wiring the Memento dev server (`uv run fastmcp run src/mcp/server.py --reload`) and the Neo4j MCP for self-validation, with credentials interpolated from `MEMENTO_NEO4J_*` env vars.
- **FR-010**: System MUST support 12-factor configuration via environment variables, with a committed `.env.example` that developers copy to `.env` without editing values.
- **FR-011**: System MUST publish the production Docker image to GitHub Container Registry (`ghcr.io`) via a GitHub Actions workflow triggered on git tags. Image tags MUST use pinned semver matching the git tag (e.g. `v0.0.2`) and be referenced by that pinned tag in the committed `docker-compose.yml`. `:latest` MUST NOT be referenced by compose — upgrades happen via explicit tag bumps in the repo, picked up by `git pull`. The published image MUST be publicly pullable without authentication, so power users need only `docker` on their machine to fetch it.
  - **Version sync policy**: `pyproject.toml` (`[project] version`) is the source of truth for the release version. Whenever `pyproject.toml` version is bumped, the developer MUST update the pinned image tag in `docker-compose.yml` in the same commit before cutting the git tag.
  - **GHCR visibility**: GitHub defaults new packages to Private. After the first successful GHA publish run, the repository owner MUST manually set the `memento` package visibility to Public in GitHub → Packages settings. This is a one-time step; without it, `docker compose pull` fails for unauthenticated users.
  - **Bootstrap sequence**: The implementation PR may be merged with `docker-compose.yml` pointing to the intended first tag (e.g. `v0.0.2`) before that image exists on ghcr.io. `main` will be transiently broken until: (1) `auto-tag.yml` (also introduced by this spec) creates and pushes the `v0.0.2` git tag from the merged version bump, (2) the publish workflow builds and pushes the image, (3) the repository owner sets GHCR visibility to Public. This window should be kept as short as possible (same session as the merge).
  - **Multi-arch**: The GHA publish workflow MUST build and push a multi-architecture manifest covering `linux/amd64` and `linux/arm64`, using `docker/setup-qemu-action` and `docker/build-push-action` with `platforms: linux/amd64,linux/arm64`. This ensures native performance on Apple Silicon Macs without requiring Rosetta 2 emulation.
  - **Auto-tagging**: System MUST include a second GHA workflow (`auto-tag.yml`) triggered on pushes to `main`. It reads the version from `pyproject.toml`, checks whether a matching git tag (e.g. `v0.0.2`) already exists, and creates and pushes the tag if it does not — which in turn triggers the Docker publish workflow. This keeps releases automatic: bumping `pyproject.toml` version in a PR is the single action that initiates a release.
- **FR-012**: Documentation MUST show MCP client configuration for connecting to the local HTTP endpoint. The preferred path is native HTTP (no bridge) for modern clients that support it (e.g. Claude Code): `{"type": "http", "url": "http://localhost:8000/mcp/"}`. For stdio-only clients (e.g. Claude Desktop) that cannot connect to HTTP servers directly, two bridge options MUST also be documented — `npx mcp-remote http://localhost:8000/mcp/` and `uvx mcp-proxy http://localhost:8000/mcp/` — letting users choose based on the runtime they already have. Neither bridge is authored or maintained by this project.
- **FR-013**: `README.md` MUST be updated with end-to-end power-user setup instructions covering: `git clone`, `docker compose up -d`, and MCP client config (native HTTP for modern clients, bridge fallback for stdio-only clients). This is the primary entry point for new users and should reflect the full install flow.

### Key Entities *(include if feature involves data)*

- **Container Image**: The immutable artifact containing Memento, its dependencies, and the embedding model.
- **Deployment Configuration**: Environment variables and CLI flags that differentiate Dev, Local, and Cloud environments.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Power users can go from `git clone` to a running Memento HTTP daemon with an MCP client connected through the bridge in under 5 minutes (excluding image pull time).
- **SC-002**: Once the Memento service reports healthy (per the FR-004 healthcheck), MCP client connects and first tool calls MUST complete within 5 seconds. The Memento lifespan hook (model load, Neo4j connection, `ensure_vector_index`) and Neo4j's own cold start (~10–30s per ADR-007) are paid during `docker compose up -d`, before the healthcheck flips green, and are exempt from this criterion.
- **SC-003**: The production Docker image contains the baked embedding model, so memory operations work offline after the image is pulled.
- **SC-004**: Zero manual steps required to wire Memento and Neo4j in the local containerized environment beyond cloning the repo, running `docker compose up -d`, and adding a single bridge entry to the MCP client config.
- **SC-005**: Importing `src.mcp.server` in a test or tool does not open a Neo4j connection or load the embedding model; those happen only when `fastmcp run` drives the lifespan hook.

## Clarifications

### Session 2026-04-27

- Q: Should `docker-compose.yml` include a healthcheck for the Memento service? → A: Yes — add `healthcheck: test: ["CMD-SHELL", "curl -f http://localhost:8000/mcp/ || exit 1"]` to the Memento service.
- Q: What is the bootstrap sequence for the first image publish? → A: Option A — merge PR with placeholder pinned tag, then cut the git tag immediately after merge to trigger GHA publish; set GHCR visibility to Public once the first run completes.
- Q: Should the GHA Docker build publish a multi-arch image? → A: Yes — `linux/amd64` + `linux/arm64` via `docker/setup-qemu-action` and `docker/build-push-action`.
- Q: Should auto-tagging (GHA creates git tag when `pyproject.toml` version bumps on `main`) be in scope? → A: Yes — add `auto-tag.yml` workflow; bumping the version in a PR is the single action that initiates a release.
