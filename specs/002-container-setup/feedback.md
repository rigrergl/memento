# Code Review — 002-container-setup

Senior-engineer review of all uncommitted changes on `feature/container-setup`, with ADR-007 and the spec/contracts as the target state. Items are grouped by severity. Line numbers reference current working-tree files.

---

## Critical (block merge)

### C1. The Memento healthcheck is unlikely to ever flip green

`docker-compose.yml:17` runs `curl -f http://localhost:8000/mcp/` against the FastMCP streamable-HTTP endpoint. MCP HTTP transport expects `POST` with specific `Accept`/`Content-Type` headers; a bare `GET` typically returns `4xx` (commonly `406 Not Acceptable` or `405 Method Not Allowed`), and `curl -f` fails on any non-2xx. If that happens, the service stays `unhealthy`, `depends_on: service_healthy` chains break for any future service, and `docker compose ps` lies to the user about readiness — directly defeating SC-002 ("first tool call within 5 s of healthy").

Verification gap: T015 (`docker compose config`) is unchecked, and **T032 (the end-to-end Flow 1 run that would have caught this) is unchecked**. The contract that prescribes this exact `test:` line was authored against an assumption nobody ran the curl against.

What to do:
1. Boot the image locally and run `curl -fv -X GET http://localhost:8000/mcp/` and `curl -fv -X POST -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' http://localhost:8000/mcp/` to see what the server actually returns.
2. If GET fails, switch the healthcheck to one of: a Python one-liner that opens a TCP socket on `:8000`, a `POST` with the correct headers, or a FastMCP-provided liveness endpoint if one exists. Update the contract and ADR alongside.

---

### C2. Resource leak in `lifespan` if `ensure_vector_index` fails

`src/mcp/server.py:18-29`:

```python
async def lifespan(_mcp):
    global config, embedder, repository, service
    config = Config()
    embedder = Factory.create_embedder(config)
    repository = Neo4jRepository(uri=..., user=..., password=...)   # driver opens here
    await asyncio.to_thread(repository.ensure_vector_index)         # <-- if this raises...
    service = MemoryService(...)
    try:
        yield
    finally:
        await asyncio.to_thread(repository.close)                   # ...this never runs
```

If `ensure_vector_index` raises (auth wrong, schema permission missing, index in failed state, transient connectivity), the Neo4j driver — already constructed — leaks. The `try/finally` is positioned below the call that is most likely to fail during startup.

Fix: open the `try` block immediately after `Neo4jRepository(...)`:

```python
repository = Neo4jRepository(...)
try:
    await asyncio.to_thread(repository.ensure_vector_index)
    service = MemoryService(...)
    yield
finally:
    await asyncio.to_thread(repository.close)
```

This is also the more standard structured-concurrency shape for a lifespan and matches what `contracts/server-lifespan.md §Required behaviour` implicitly assumes.

---

## High

### H1. `.env.example` undermines the "no default password" decision

`.env.example:4-6`:

```
# For local development with the provided docker-compose, use: memento-password
# (Neo4j requires a minimum of 8 characters)
MEMENTO_NEO4J_PASSWORD=
```

ADR-007 explicitly rejected shipping a default password ("it normalises a credential that ends up identical across every deployment, creates a false impression of 'configured' security, and trains users not to think about secrets"). Suggesting `memento-password` in the comment is the same failure mode in different clothing — every user who copy-pastes the example will be running with the same shared secret, exactly the situation the ADR amendment removed `:-memento` to prevent. Two of the three published bridge configs target `localhost`, so cross-tenant bleed isn't immediate, but this is still a credential drift hazard.

The ADR amendment shows the intended shape: blank value with only the 8-char-minimum comment.

Fix: drop the "use: memento-password" suggestion. Keep just the 8-char minimum hint. Optionally add a generation hint such as `# e.g. openssl rand -base64 12`.

### H2. README is missing the bootstrap-window callout (FR-011 §Bootstrap)

T019 explicitly required: "add a Bootstrap-window callout per FR-011 §Bootstrap warning that `docker compose pull` fails until the maintainer cuts the first tag and sets GHCR visibility to Public". `README.md` has no such callout. Until the first `publish.yml` succeeds *and* the maintainer toggles the GHCR package to Public, every new user's `docker compose up -d` fails on `docker compose pull` with `denied` / `manifest unknown`. The README walks them straight into that error with no explanation.

Fix: add a short admonition under "Power-User Setup" along the lines of:

> **First-publish bootstrap**: until v0.0.2 has been built and the GHCR package visibility is set to Public, `docker compose pull` returns `manifest unknown`. Track first-publish status at <https://github.com/rigrergl/memento/pkgs/container/memento>.

This can come down once the bootstrap is past, but it has to be present for the merge window itself.

### H3. Dockerfile: runtime stage `chown` is not recursive — `app` user cannot write under `/app`

`Dockerfile:25-30`:

```dockerfile
RUN useradd --system --create-home --uid 1001 app && chown app /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/.cache/models /app/.cache/models
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
```

`chown app /app` only changes the directory inode, not its contents. The subsequent `COPY --from=builder` retains root ownership on `.venv`, `src`, `.cache/models`, and `pyproject.toml`. The `app` user can read/execute via mode bits but cannot write. Specific risks:

1. Sentence-transformers / HuggingFace can touch lock files inside `cache_folder` during loading. Even when the model is fully present, `transformers`/`safetensors` may attempt write probes; read-only failure here will manifest as a runtime crash on first inference, not at boot.
2. `fastmcp run --reload` uses watchfiles and may write to `__pycache__` directories under `src/`. Read-only `__pycache__` produces verbose `PermissionError` warnings on every reload (not used by the published image, but the same Dockerfile is reused if dev ever moves into the container).
3. Any future temp-file logic (rotating logs, intermediate write paths) silently breaks.

Fix: either `COPY --chown=app:app --from=builder ...` on every COPY, or run `chown -R app:app /app` *after* the COPYs but before `USER app`. Prefer `--chown=` for layer-cache friendliness.

### H4. `Neo4jRepository.close` is not idempotent

T010's task description specified: "calls `self._driver.close()` if it has not yet been closed (idempotent)". `src/graph/neo4j.py:77-79`:

```python
def close(self) -> None:
    """Close the Neo4j driver connection."""
    self._driver.close()
```

No idempotency guard. Current versions of the Neo4j Python driver tolerate double-close, so this is not (yet) a runtime failure, but the contract is unmet, and a future driver upgrade or a test that double-enters/exits the lifespan will trip on it. Add a `_closed: bool` flag and short-circuit.

---

## Medium

### M1. Several Polish-phase verification tasks are unchecked

`tasks.md` shows T015, T027–T034 unchecked. T015 (`docker compose config`), T027 (`docker build`), T028 (multi-arch buildx), T029 (offline embedding), T030 (curl present), T031 (non-root), T032/T033 (Flow 1/Flow 2 end-to-end) collectively cover every infrastructure artifact that has no unit-test surface. Skipping them is exactly what `plan.md`'s Quality Gate 5 was meant to prevent — and would have surfaced C1 and H3 directly.

Either run them now or document why they're deferred. T032/T033 are gated on the bootstrap window per the spec, but T015 and T027–T031 can run today against a locally-built image.

### M2. `embedder` lacks the type hint that the other module-level placeholders have

`src/mcp/server.py:12-15`:

```python
config: Config | None = None
embedder = None
repository: Neo4jRepository | None = None
service: MemoryService | None = None
```

`embedder` should be `IEmbeddingProvider | None = None` for symmetry and so type checkers can flag misuse. Trivial.

### M3. Test helper `_get_tool_fn` spins up an event loop per call

`tests/test_mcp/test_server.py:25-29`:

```python
def _get_tool_fn(tool_name: str):
    from src.mcp.server import mcp
    tool = asyncio.run(mcp.get_tool(tool_name))
    return tool.fn
```

Each `remember`/`recall` test pays a fresh `asyncio.run` per call. Functional but wasteful, and `asyncio.run` has surprising behaviour around already-running loops (won't matter in the current sync tests but will if anyone refactors). Two cleaner options:

- A module-level fixture that resolves both tool fns once and yields them.
- Move the tests to `pytest-asyncio` style and `await mcp.get_tool(...)` directly.

### M4. AGENTS.md hardcodes the current spec path

`AGENTS.md:78`:

```diff
-shell commands, and other important information, read the current plan
+shell commands, and other important information, read the current plan:
+[specs/002-container-setup/plan.md](specs/002-container-setup/plan.md)
```

This will go stale on every new spec. Either keep the link generic ("the most recent plan under `specs/`") or rely on `.specify/feature.json` (already pointing at the active feature dir) and have AGENTS.md describe how to discover the plan rather than hardcoding it. As-is, every future spec has to remember to update this line, and it'll quietly drift.

### M5. publish.yml multi-arch build of sentence-transformers under QEMU is untested

`linux/arm64` is built via QEMU emulation in `publish.yml`. The Dockerfile bakes `sentence-transformers/all-MiniLM-L6-v2` inside the build stage, which means the model download + Python import happens under emulation on the arm64 leg. This typically works but can take 5–10× longer than native; the model bake under QEMU has been known to push past GHA `ubuntu-latest` job-timeout windows. No data here yet because the workflow has never run — flagging as a known unknown that will surface during the bootstrap. Mitigations if it bites: split the matrix per platform (native arm64 runners now exist on GHA), or move the model-bake step to a `--platform=$BUILDPLATFORM` stage so it runs on the native host.

### M6. `auto-tag.yml` has a TOCTOU race on concurrent merges to main

The "skip if tag exists" check uses `git rev-parse` against the local clone, then pushes. With `cancel-in-progress: false`, two PRs that land back-to-back can both pass the check before either pushes; the second `git push origin v$VERSION` then fails (non-fast-forward / tag exists). Failure mode is loud and recoverable (just re-run), not silent, so it's medium not high. Worth a comment in the workflow noting the assumption of low-cadence releases.

---

## Low / Nits

### L1. `tests/test_mcp/test_lifespan.py` patches the global `asyncio.to_thread`

`patch("asyncio.to_thread", new_callable=AsyncMock)` patches the module attribute on the `asyncio` package, which is shared globally. Functionally fine because Python module identity is shared, but `patch("src.mcp.server.asyncio.to_thread", ...)` is the more idiomatic, narrower form and won't surprise anyone reading the test in isolation.

### L2. Dockerfile copies `pyproject.toml` into the runtime stage

`Dockerfile:30`. The contract says "so `fastmcp` can find project metadata if needed". `fastmcp run` operates on the source-file path, not project metadata; `.venv/bin/fastmcp` is already self-contained. Worth verifying the runtime actually uses this and dropping the COPY if not — every byte counts on a published multi-arch manifest.

### L3. `.env.example` lists vars the power-user compose ignores

`.env.example:1-2,9-14` set `MEMENTO_NEO4J_URI`, `MEMENTO_NEO4J_USER`, and the `MEMENTO_EMBEDDING_*` block. The compose YAML hardcodes all of these; only `MEMENTO_NEO4J_PASSWORD` is read from `.env` via substitution. Power users editing these values in `.env` will see no effect on the running container — confusing. Two options: (a) section the file with `# Dev-only — ignored by docker-compose` headers, or (b) ship two example files (`.env.example` for dev, `.env.power-user.example` with just the password). Option (a) is lower-effort.

### L4. Cache-dir contract is implicit and brittle

The Dockerfile bakes the model to `/app/.cache/models`; `Config.embedding_cache_dir` defaults to `.cache/models` (relative); they reconcile only because `WORKDIR /app` is set in the runtime stage. Anyone changing one side has no static signal to change the other. A one-line comment in the Dockerfile pointing at `Config.embedding_cache_dir`'s default (or vice versa) would prevent the next maintainer from breaking offline mode silently.

### L5. ADR-007 example uses `v0.2.0`, real compose uses `v0.0.2`

The ADR's docker-compose excerpt shows `image: ghcr.io/rigrergl/memento:v0.2.0`. The real `docker-compose.yml` is `:v0.0.2`. The ADR is "illustrative" per its prose, so this is minor doc-vs-code drift, but worth aligning to avoid confusion when someone diffs the two.

### L6. Two import styles for `src.mcp.server` inside the same test file

`tests/test_mcp/test_server.py` uses both `import src.mcp.server as server_module` (for `patch.object`) and `from src.mcp.server import mcp` (inside `_get_tool_fn`). Pick one — the module-level `server_module` reference would be fine for both.

### L7. `embedder` global is reassigned but never read

The lifespan populates `embedder`, but no test asserts on it specifically and no production code reads `server_module.embedder`. If we want to keep it as a hook for future tests, fine; if not, it could be a local in `lifespan`. Pure YAGNI nit, mentioned only because the codebase explicitly cites YAGNI in CLAUDE.md.

---

## Things I checked and was satisfied with

- Lifespan refactor cleanly removes the `__main__` block; tool bodies still read `service` from module scope at call time, preserving the existing `patch.object(server_module, "service", ...)` pattern.
- `Config.mcp_host` / `Config.mcp_port` deletion (FR-007 / TD-003) is clean — no shim, no dead reference, test asserts the absence directly.
- `127.0.0.1` binding on every host port (FR-005) — Memento, Neo4j Bolt, Neo4j browser — all correct.
- `${MEMENTO_NEO4J_PASSWORD:?...}` form on both services means compose fails at config-time with a useful message, not a runtime auth error. Good.
- `.dockerignore` excludes `.git`, `.venv`, `tests/`, `specs/`, `Documentation/`, `.devcontainer/`, `.github/`, `*.md`, caches — keeps build context tight.
- Multi-arch publish workflow shape (`setup-qemu` → `setup-buildx` → `metadata-action` → `build-push-action` with `platforms: linux/amd64,linux/arm64`) is the canonical form and has no `:latest` tag.
- TD-003 marked Resolved, TD-004 has the interim-resolution status update — ledger is honest.
- README split into Power-User / Developer sections with the right "use this if…" admonitions; three MCP client config blocks (native HTTP + two bridges) match FR-012.
- `.devcontainer/` cleanly deleted; no leftover references in `README.md`.

---

## Open questions for the author

1. Was the `curl -f http://localhost:8000/mcp/` healthcheck ever exercised against a running image? (See C1.) If yes, what response code did FastMCP return?
2. Were T032 / T033 deferred deliberately, or just not run yet? If deferred, what's the gating signal — first publish completing?
3. The `.env.example` "use: memento-password" comment — was that a deliberate convenience for first-time users, or an oversight against H1? If deliberate, please call out the trade-off in the ADR consequences section so the next reviewer doesn't re-litigate.
