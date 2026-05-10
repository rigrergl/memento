# Feature Specification: 003-container-polish-devloop

**Feature Branch**: `003-container-polish-devloop`
**Created**: 2026-05-06
**Status**: Draft
**Input**: User description: "Address high-level feedback from `specs/002-container-setup/feedback.md` so the power-user container setup is genuinely polished, then validate the developer dev loop end-to-end so AI coding agents can edit Memento and verify their own changes (closed by making one small contract change to an existing tool)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Power-User Setup Is Production-Ready (Priority: P1)

As a new power user, I want `docker compose up -d` to result in a stack that reliably reports `healthy`, recovers cleanly from transient startup failures, and does not invite me to copy-paste a shared default password — so I can trust the deployment without reading code-review threads.

**Why this priority**: 002-container-setup shipped a working but rough power-user surface. The current setup fails or misleads on at least four common paths: a healthcheck shape that may never flip green, a driver leak when index creation fails, an `.env.example` hint that normalizes a shared password, and a README that walks first-time users into a `manifest unknown` error during the publish-bootstrap window. Without this polish, every new user encounters at least one of these.

**Independent Test**: On a clean machine with Docker, `git clone … && cd memento && cp .env.example .env`, set a password, `docker compose up -d`, verify both services report `healthy`, then exercise `remember`/`recall` via an MCP client. Verify `.env.example` and the README do not contain the misleading guidance flagged by the review.

**Acceptance Scenarios**:

1. **Given** a fresh `docker compose up -d` against the published image (or a locally-built equivalent), **When** Neo4j's healthcheck flips green and the Memento lifespan completes, **Then** `docker compose ps memento` reports `healthy` (not `starting` indefinitely or `unhealthy`).
2. **Given** Memento startup encounters a failure during `ensure_vector_index` (auth wrong, schema permission missing, transient connectivity), **When** the lifespan unwinds, **Then** the Neo4j driver is closed and no driver/session leak is observable.
3. **Given** the user opens `.env.example`, **When** they read the file, **Then** they are not invited to copy-paste a specific shared example password; only the 8-character minimum is documented (with an optional generation-command hint).
4. **Given** the running container, **When** the application code or its dependencies write to paths under `/app` during normal operation (e.g., embedding-cache lock files, Python `__pycache__`), **Then** writes succeed without `PermissionError`.

---

### User Story 2 - Dev Loop Is Validated End-to-End (Priority: P1)

As an AI coding agent (or developer) working on Memento, I want to edit a tool, see my edit reflected on the next tool call, and self-validate the database state — so I can iterate on Memento autonomously and have confidence in my changes before opening a PR.

**Why this priority**: ADR-007's whole motivation for the dev loop is making Memento changes safely automatable by LLMs. The `.mcp.json` artifact has shipped, but the loop has never been exercised end-to-end. This spec closes that gap by both fixing any rough edges discovered during the exercise and proving the loop with a small, real change.

**Independent Test**: With Neo4j running locally, launch an MCP client (Claude Code or Gemini CLI) at the repo root with the project-level `.mcp.json` honoured; it lists the `memento` MCP server. Edit a tool's parameter descriptions to include new behavioural detail. Confirm that on the next tool call, the client/agent sees the new description, while the underlying behaviour is unchanged. Verify a `remember`/`recall` cycle via a direct `cypher-shell` query against the Neo4j container.

**Acceptance Scenarios**:

1. **Given** a fresh clone with `.env` configured and `docker compose up neo4j -d` running, **When** the developer launches an MCP client (Claude Code or Gemini CLI) at the repo root with the project-level `.mcp.json` honored, **Then** the client connects to the `memento` MCP server (via `uv run fastmcp run … --reload`).
2. **Given** the dev server is running under `--reload`, **When** the developer edits a tool's parameter descriptions in `src/mcp/server.py` and saves, **Then** within at most one round-trip the next listing or call reflects the new description (the worker has restarted, the agent's client has respawned the subprocess).
3. **Given** the dev server is running, **When** the developer/agent issues a `remember` followed by a `recall` call, **Then** running `cypher-shell` against the Neo4j container confirms a `Memory` node exists with the stored content.
4. **Given** the dev loop has been validated, **When** the small contract change made during validation lands on `main`, **Then** it does so as a real improvement (not a throwaway edit) — i.e., the parameter descriptions added carry actual informational value about the tools' behaviour.

---

### User Story 3 - Repository Hygiene Cleanup (Priority: P3)

As a maintainer, I want trivial review-flagged drift cleaned up — hardcoded spec paths, missing type annotations, minor inconsistencies — so the repo's signal-to-noise stays high without revisiting these in a future review.

**Why this priority**: None block users; all are low-cost. Bundling them in this spec is cheap and avoids stale items accumulating.

**Independent Test**: Search the repo for the documented hardcoded references and confirm they are gone or generalized. Confirm module-level placeholders carry consistent annotations.

**Acceptance Scenarios**:

1. **Given** `AGENTS.md` after this spec lands, **When** the next spec is created, **Then** `AGENTS.md` does not need a manual edit to point at the new spec — references are either generic or driven by `.specify/feature.json`.
2. **Given** `src/mcp/server.py` after this spec lands, **When** a reader audits the file, **Then** only `service` remains as a module-level global (with `MemoryService | None = None` annotation); `config`, `embedder`, and `repository` are local variables in `lifespan`.

---

### Edge Cases

- Some MCP clients cache tool descriptions per session and only refresh on reconnect; the dev-loop validation must observe the new description after a worker respawn (which `--reload` triggers), not necessarily within a single client session.
- The healthcheck fix requires an image rebuild and republish (`v0.0.3`) before validation against the published image is possible. Validation runs against a locally-built image first; the published image is verified once the new tag ships in this spec's PR.
- A feedback item may be discovered to be Not-Applicable during work (e.g., already fixed in flight, or moot due to another change). The spec accommodates this: such items are recorded with rationale in Assumptions and removed from the open-feedback ledger.

---

## Clarifications

### Session 2026-05-07

Resolutions recorded against `research/clarification-questions.md`. The questions document remains the long-form record of *why*; this section captures the decisions in the spec itself.

**Cross-cutting**

- **All performance/timing constraints are dropped from this spec.** The previously written "60s healthy" (SC-001), "5s reload reflection" (SC-003), and "5min dev-loop round-trip" (SC-007) figures originated from the prior model's recommendation, not the maintainer. They are removed below. Future timing concerns are deferred to a follow-up spec only if they become a real pain point.
- **Bootstrap window is closed.** `v0.0.2` is published to GHCR and the package visibility is Public. FR-005's callout is therefore Not-Applicable; H2 in the feedback ledger flips to NA.
- **Single PR** for the whole spec — power-user polish, hygiene, and dev-loop validation land together.
- **Version bump**: this spec's completion ships `v0.0.3` of the published image (bundled in the same PR).

**Healthcheck (FR-001)**

- FastMCP does not ship a built-in liveness endpoint, and the MCP protocol does not define one; community pattern is a `@custom_route("/health")` returning HTTP 200. Plan stage chooses between (a) adding the custom route + `curl -f http://localhost:8000/health` healthcheck, or (b) keeping the curl probe but switching to a POST + `initialize` MCP handshake. Either is acceptable; (a) is simpler.
- `start_period` / `interval` / `timeout` / `retries` are out of scope for this spec; current values stay.

**Lifespan + driver lifecycle (FR-002, FR-003)**

- FR-002 fix: open the `try` block immediately after `Neo4jRepository(...)` per `feedback.md §C2`. There is a real leak path today if `ensure_vector_index` raises.
- FR-003 (idempotent `Neo4jRepository.close`) is **deferred** to `Documentation/known-tech-debt.md` as low-priority debt. Current Neo4j driver tolerates double-close, so it is a contract gap rather than a runtime bug.

**Image filesystem permissions (FR-006)**

- Use a trailing `RUN chown -R app:app /app` after all COPYs (rather than per-COPY `--chown=`). Layer-cache cost is negligible for this image; simpler diff. Add `--user-group` to `useradd` so `app:app` resolves cleanly.

**Module globals (FR-012)**

- Convert `config`, `embedder`, and `repository` to local variables inside `lifespan`. Only `service` remains at module scope (so `patch.object(server_module, "service", ...)` continues to work in tests). FR-012 reflects this scope rather than the original "annotate all four placeholders" wording.

**Dev-loop contract change (FR-013)**

- Scope the contract change to **adding parameter descriptions** to `remember` and `recall`. Use `Documentation/legacy/mcp-tool-specification.md` for stylistic vibe (concise, behavioural, parameter-focused) — but ignore its now-defunct features (`source`, `supersede_memory`).

**Dev-loop validation (FR-008)**

- The dev loop is exercised on **both Claude Code and Gemini CLI**. Cursor is left untested (recorded as such in `verification.md`).
- The Neo4j DB-state probe uses **`cypher-shell` (Neo4j CLI) directly**, not `mcp-neo4j-cypher`. The `neo4j-cypher` MCP server entry is removed from `.mcp.json`.
- Validation flow per client: (1) launch the client at the repo root, (2) give the agent a canonical prompt to add a tool description, edit it, observe the change on next call, run `remember` then `recall`, then issue a `cypher-shell` query confirming the `Memory` node exists, (3) maintainer reviews the agent's transcript plus runs the `cypher-shell` query independently to confirm DB state.
- `verification.md` (committed alongside the spec) captures: the canonical prompt, the canonical `cypher-shell` query, and the per-client transcripts/observations.

**Power-user verification (FR-007)**

- Verification result is recorded in `specs/003-container-polish-devloop/verification.md` (committed alongside the spec) and summarised in the PR description.
- "Someone" performing the verification (per the prior SC-007 wording) is a **fresh AI coding agent**, matching ADR-007's motivation. The maintainer reviews the transcript.

**Feedback ledger triage (FR-009 / FR-010)**

- Resolutions per the table in `research/clarification-questions.md §I`. Net effect: C1, C2, H1, H3, M1, M2, M4, L7 → **Resolved**; H2 → **NA**; H4, M3, M5, M6, L1, L2, L3, L4, L5, L6 → **Deferred to known-tech-debt.md**.
- New tech-debt entries follow the existing template (TD-001..TD-004 style) and adopt a new **Priority** field (`high` / `low`). M5 and M6 are high; the rest of the deferred items are low. Existing entries TD-001..TD-004 gain the priority field too.
- "Remediation: N/A — advisory-only" is admitted as a sentinel for advisory-only debt entries (e.g., M6).

**AGENTS.md path discovery (FR-011)**

- AGENTS.md reads `.specify/feature.json`'s `feature_directory` and links `<feature_directory>/plan.md` (or describes the discovery path so an agent can resolve it). `CLAUDE.md` / `GEMINI.md` are left as `@AGENTS.md` delegates.

**Other items rolled in**

- **README "Developer Setup"** gains: launching ritual for both Claude Code and Gemini CLI (e.g., `set -a; source .env; set +a` or `direnv allow`); a troubleshooting note on stale `neo4j_data` volume after a password change (run `docker compose down -v` to wipe); a Python-version note that defers to `pyproject.toml`'s `requires-python` rather than hardcoding a version; a Bolt-port-reachability note.
- **`specs/002-container-setup/contracts/server-lifespan.md`** gains a one-line invariant note that the embedder is reentrant/resource-free; only the Neo4j driver leaks if mishandled.
- **Plan stage** re-verifies time-sensitive dependencies (FastMCP, neo4j-driver, sentence-transformers) before ship per the project's `AGENTS.md` directive.
- **`--reload` watcher behaviour for transitive imports** is verified as part of FR-008's dev-loop exercise; any limitation found is documented in README.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST update the Memento container healthcheck so it transitions to `healthy` within the configured `start_period` under normal conditions and accurately reflects HTTP-MCP readiness. The healthcheck MUST NOT depend on a request shape that the running transport rejects with a non-2xx response (e.g., a bare `GET` against an MCP endpoint that requires `POST` with specific `Accept`/`Content-Type` headers).
- **FR-002**: The server `lifespan` MUST close the Neo4j driver if any step after driver construction (including `ensure_vector_index`, `MemoryService` construction, or the body of the `yield`) raises. No driver or session leak on startup failure.
- **FR-003**: ~~`Neo4jRepository.close` MUST be safe to call multiple times.~~ **Deferred** to `Documentation/known-tech-debt.md` as low-priority debt; the current Neo4j driver tolerates double-close, so this is a contract gap rather than a runtime bug. (See Clarifications §"Lifespan + driver lifecycle".)
- **FR-004**: `.env.example` MUST NOT include guidance suggesting a specific value for `MEMENTO_NEO4J_PASSWORD`. Only the 8-character minimum requirement may appear; an optional generation-command hint (e.g., `openssl rand -base64 12`) is permitted.
- **FR-005**: ~~README Bootstrap-window callout.~~ **Not Applicable** — bootstrap is closed (`v0.0.2` published, GHCR Public). Recorded in Assumptions §"Feedback Items Recorded as Not-Applicable" as H2.
- **FR-006**: The runtime image MUST grant the runtime user write access to every path the application or its dependencies read or write during normal operation, including embedding-cache directories under `/app` and Python module caches under `src/`.
- **FR-007**: Power-user end-to-end verification MUST be performed and the result recorded in `specs/003-container-polish-devloop/verification.md` (committed alongside the spec) and summarised in the PR description before this spec is considered complete: a clean-machine `git clone` → `docker compose up -d` → both services report `healthy` → `remember`/`recall` round-trip succeed via an MCP client. Verification runs against a locally-built image first; the `v0.0.3` published image is verified once cut.
- **FR-008**: The dev loop MUST be exercised end-to-end on **both Claude Code and Gemini CLI** before this spec is considered complete. For each client:
  - The agent is launched at the repo root, with the project-level `.mcp.json` honoured. `.mcp.json` registers the `memento` MCP server (via `uv run fastmcp run … --reload`); `mcp-neo4j-cypher` is **removed** from `.mcp.json` — DB-state probes are performed via `cypher-shell` (Neo4j CLI) instead.
  - A small, real contract change to an existing tool (parameter-description enrichment per FR-013) is committed by the agent; the new contract is observable on the next tool call after `--reload` triggers (next round-trip after the worker respawns).
  - A `remember`/`recall` cycle is followed by a `cypher-shell` query that confirms a `Memory` node exists with the stored content.
  - The canonical prompt, canonical `cypher-shell` query, per-client transcripts, and any client-specific caveats (e.g., subprocess respawn behaviour) are recorded in `verification.md`.
- **FR-009**: Each Critical and High feedback item documented in `specs/002-container-setup/feedback.md` (C1, C2, H1, H2, H3, H4) MUST be either resolved by this spec or appended to `Documentation/known-tech-debt.md` with a documented rationale for deferral. There MUST NOT be any Critical or High items left in an undocumented state when this spec ships.
- **FR-010**: Each Medium and Low feedback item from `specs/002-container-setup/feedback.md` (M1–M6, L1–L7) MUST be either resolved by this spec, appended to `Documentation/known-tech-debt.md`, or recorded as Not-Applicable in this spec's Assumptions section with rationale. No Medium or Low item may be left silently unaddressed.
- **FR-011**: Project-level guidance documents (`AGENTS.md` and any symlinks/aliases such as `CLAUDE.md`/`GEMINI.md`) MUST NOT hardcode a single feature directory. References to "the current spec" or "the current plan" MUST be path-discovery-driven (e.g., based on `.specify/feature.json`) or use a generic phrasing that does not require manual edits per feature.
- **FR-012**: `src/mcp/server.py` MUST convert `config`, `embedder`, and `repository` from module-level globals to local variables inside `lifespan`. Only `service` remains at module scope (so `patch.object(server_module, "service", ...)` continues to work). The remaining `service` placeholder MUST carry the `MemoryService | None = None` annotation form.
- **FR-013**: The dev-loop contract change MUST land as a real improvement on `main` rather than a throwaway edit. Concretely: parameter descriptions MUST be added to **both** `remember` and `recall` tool functions (covering `content`, `confidence`, `query`, `limit`), expressed in a way that is concise, behavioural, and parameter-focused. `Documentation/legacy/mcp-tool-specification.md` is the stylistic reference for vibe; the legacy file's now-defunct features (`source` field, `supersede_memory`) are NOT re-introduced.

### Key Entities *(include if feature involves data)*

- **Power-User Setup**: The end-to-end flow from `git clone` through a healthy running stack to the first successful MCP tool call. Owns: container healthcheck, image runtime semantics, README onboarding, environment-file guidance.
- **Dev Loop**: The end-to-end flow from a developer/agent edit to the next tool call exercising the new code. Owns: `.mcp.json` (`memento` server only), the `--reload` watcher, and `cypher-shell` (Neo4j CLI) for direct DB-state probes.
- **Feedback Ledger**: The open state of `specs/002-container-setup/feedback.md`. Each item is in one of three terminal states after this spec: Resolved (fixed in code/docs by this spec), Deferred (appended to `Documentation/known-tech-debt.md` with rationale), or Not-Applicable (recorded in this spec's Assumptions with rationale).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a clean machine, `git clone` → fill in `.env` → `docker compose up -d` results in `docker compose ps` reporting both services `healthy`. No service stays in `starting` indefinitely or flips to `unhealthy` on the normal-conditions path. (Wall-clock target deliberately omitted; see Clarifications.)
- **SC-002**: An induced startup failure in any step of `lifespan` (verified by code review of the try/finally placement and the existing lifespan test path) leaves zero leaked Neo4j driver instances, observable by absence of "session not closed" or driver-leak warnings on shutdown.
- **SC-003**: A developer or coding agent editing a tool description in `src/mcp/server.py` sees the new description on the next tool listing or call after `--reload` triggers a worker respawn. (Some MCP clients cache tool descriptions per session and only refresh on reconnect; in those clients, the next round-trip following the subprocess respawn reflects the change.)
- **SC-004**: 100% of Critical and High feedback items from `specs/002-container-setup/feedback.md` are either fixed in code/docs or recorded in `Documentation/known-tech-debt.md` with rationale. Reviewer can verify by diffing the feedback file's open items against the tech-debt ledger.
- **SC-005**: 100% of Medium and Low feedback items are either fixed, recorded in `Documentation/known-tech-debt.md`, or marked Not-Applicable in this spec's Assumptions with rationale.
- **SC-006**: A power-user copy-pasting only the README and `.env.example` content cannot end up running with a credential that another Memento user could guess from public guidance. Verification: textual review of `.env.example` and the README confirms neither suggests a specific password value.
- **SC-007**: After this spec ships, a fresh AI coding agent (Claude Code or Gemini CLI) following the README's Developer Setup can complete the dev loop round-trip — edit a tool description, observe the new description through the MCP client, run `cypher-shell` against Neo4j to confirm DB state of a `remember`/`recall` cycle — without the maintainer's intervention. (Wall-clock target deliberately omitted; see Clarifications.)

## Assumptions

- The publish bootstrap for `v0.0.2` (image pushed to GHCR, package set to Public) is **closed** as of 2026-05-07. FR-005's callout is therefore Not-Applicable.
- The dev-loop validation runs against the local repo via `uv run fastmcp run --reload`, not against the published Docker image. The image is for power-user distribution; the dev loop is native VM-only per ADR-007.
- The "small contract change" used to validate the dev loop (FR-008, FR-013) is parameter-description enrichment on `remember` and `recall`. This is purely additive, has zero behavioural risk, and is observable to MCP clients via tool listings.
- Items in the feedback file that are future-only risks or low-priority polish are recorded in `Documentation/known-tech-debt.md` (with a new `Priority` field of `high` or `low`) rather than gating this spec.
- The "Resolved" state for an item in this spec means addressed in code, docs, configuration, or contract. Verification of the published-image-side of changes runs against `v0.0.3` once cut as part of this spec's PR.
- Performance and timing constraints are deliberately excluded from this spec; they will be revisited in a follow-up spec only if they become a real pain point.

### Feedback Items Recorded as Not-Applicable

- **H2** (README bootstrap callout): Bootstrap window closed (2026-05-07). The callout would be vestigial; FR-005 is recorded as NA.
