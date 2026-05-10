# Clarification Questions — 003-container-polish-devloop

**Created**: 2026-05-06
**Mode**: "Grill me" — every ambiguity, edge case, and unstated decision I could find while reading `spec.md`, the 002 `feedback.md`, ADR-007, the current `docker-compose.yml`, `src/mcp/server.py`, `.env.example`, and `.mcp.json`. Answer in a fresh chat; the goal is for the answers to flow back into `spec.md` (and where appropriate into `Assumptions`, `Documentation/known-tech-debt.md`, or task-level decisions during `/speckit-plan`).

The format for each question:

- **Why it matters**: what downstream choice this unlocks/blocks.
- **Options** (where applicable): a short menu, with my recommendation flagged.
- Some questions ask for a value (number, snippet, file name) instead of a choice.

There are 60 questions, grouped by area. Skip any that feel obviously already-answered to you — but please record the answer somewhere even when "obvious", because the spec presently underspecifies most of these.

---

## A. Healthcheck redesign (FR-001 / C1)

**A1. Which healthcheck shape do you want to commit to?**
*Why it matters*: this is the single most important fix in the spec; the choice ripples into the docker-compose contract, the Dockerfile (does `curl` still need to be present?), and what "verified working" means for SC-001.

| Option | Description |
|--------|-------------|
| A | Python one-liner that opens a TCP socket to `127.0.0.1:8000` (`python -c "import socket;socket.create_connection(('127.0.0.1',8000),1).close()"`). Cheapest to make work; verifies the listener exists, not that MCP itself is responsive. |
| B (Recommended) | `curl -fsS -X POST -H 'Accept: application/json, text/event-stream' -H 'Content-Type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"healthcheck","version":"0"}}}' http://127.0.0.1:8000/mcp/`. Actually exercises the MCP protocol; requires `curl` to remain in the runtime image. |
| C | A FastMCP-provided liveness endpoint if one exists. Need to verify upstream — current FastMCP 3.x does not expose one I can confirm. |
| D | TCP socket via Python AND a small in-process readiness flag (e.g., the lifespan toggles `mcp._ready=True` after `ensure_vector_index`). Most accurate but requires application code in support of the healthcheck. |

*Recommendation*: **B**, because (a) it actually proves MCP is talking and `lifespan` finished, (b) it doesn't require touching application code, (c) the runtime image already ships `curl` per H3, and (d) C1 in feedback explicitly suggested testing this exact shape.

**A2. If you pick (B), what HTTP status do you want the healthcheck to require?**
*Why it matters*: FastMCP's streamable-HTTP transport returns 200 with an SSE body for `initialize`; some setups return 202. `curl -f` rejects 4xx/5xx. Confirm 2xx only, or relax to "any non-5xx".

**A3. What `start_period`, `interval`, `timeout`, and `retries` should the new healthcheck use?**
*Why it matters*: SC-001 says "healthy within 60s"; current values are `start_period: 30s, interval: 10s, timeout: 5s, retries: 6` (=> max ~90s before unhealthy). The 60s target requires either tighter values or a tighter `start_period`.

| Option | start_period | interval | timeout | retries | Worst-case to healthy |
|--------|-------------|----------|---------|---------|----------------------|
| A | 30s | 5s | 3s | 6 | ~60s |
| B (Recommended) | 20s | 5s | 3s | 8 | ~60s, more retries during model load |
| C | 60s | 10s | 5s | 6 | ~120s, looser but breaks SC-001 |

*Recommendation*: **B** — model-bake means lifespan startup typically takes 5–15s; 8 retries gives slack for slow `to_thread` import on arm64.

**A4. Should the healthcheck contract be codified anywhere besides `docker-compose.yml`?**
*Why it matters*: 002 had a `contracts/docker-compose.md`. Should this spec produce its own `contracts/healthcheck.md`, update the 002 contract in-place, or leave the contract implicit in compose?

**A5. The published `v0.0.2` image already has the broken healthcheck. Do you want this spec to ship a `v0.0.3` (or `v0.1.0`) tag bump as part of completion?**
*Why it matters*: until a fixed image is published, FR-001 only holds for locally-built images; SC-001 against the published image is a future event. Recommendation: **yes, ship a follow-on tag bump** — otherwise FR-007's "verification against the published image" is forever in limbo.

**A6. If A5=yes, do you want the version bump and publish to land in this spec's PR, or as a follow-up "release" PR after merge to `main`?**
*Why it matters*: bundling the bump with the fix means `docker compose up -d` for a power user works the moment this spec ships; splitting means a brief window where `main` references a pinned image that doesn't yet exist again.

---

## B. Lifespan failure paths (FR-002 / C2)

**B1. Should the lifespan also guard against `Factory.create_embedder` failing?**
*Why it matters*: today's lifespan calls `create_embedder` *before* opening the Neo4j driver. If that raises (e.g., model bake missing in dev), nothing leaks. But if the order changes (someone defers embedder creation past driver creation), that becomes a leak path. Spec only requires the driver to close on post-driver failures. Decide: codify the order, or wrap embedder creation in the same try/finally?

| Option | Description |
|--------|-------------|
| A (Recommended) | Spec the order: embedder is constructed before driver; the try/finally opens immediately after `Neo4jRepository(...)`. Document this constraint. |
| B | Wrap the whole lifespan body in a single try/finally that closes whatever was constructed. More defensive; slightly more code. |

*Recommendation*: **A**, simpler, matches the C2 fix shape exactly. Add a one-line comment in `lifespan` documenting the invariant.

**B2. Do you want a unit test that injects a failure into `ensure_vector_index` and asserts `repository.close` was called exactly once?**
*Why it matters*: SC-002 demands "verified by injecting a failure into the post-driver-construction path" but no test currently does this. If yes, decide: monkeypatch `Neo4jRepository.ensure_vector_index` to raise, or use `unittest.mock.patch.object`?

**B3. What error message (if any) should `lifespan` log on driver-close failure during teardown?**
*Why it matters*: `repository.close` itself can theoretically raise (e.g., if the driver is already in a broken state). FR-002 says "no driver/session leak" — but `try/finally` re-raises. Should we swallow, log, or both? Currently the codebase has no logger configured (TD-001). Recommendation: **leave as-is** — silence-on-teardown is consistent with the rest of the codebase, and TD-001 is the right place to fix observability holistically, not here.

**B4. Should the lifespan also handle `KeyboardInterrupt` / `asyncio.CancelledError` cleanly during the `yield`?**
*Why it matters*: `try/finally` already covers it. Worth confirming you don't want explicit handling. Recommendation: **no, finally is enough**.

---

## C. Idempotent close (FR-003 / H4)

**C1. Idempotency mechanism: a `_closed` flag, or wrapping the call in `contextlib.suppress` of driver-already-closed exceptions?**

| Option | Description |
|--------|-------------|
| A (Recommended) | `_closed: bool = False` flag, set in `close()` before calling `self._driver.close()`, with early return on subsequent calls. Matches H4's wording. |
| B | `try: self._driver.close() except neo4j.exceptions.DriverError: pass`. Tolerant but masks real errors. |

*Recommendation*: **A** — explicit, no swallowed exceptions, matches H4 verbatim.

**C2. Should the idempotency be tested?**
*Why it matters*: H4 says "future driver upgrade or test that double-enters/exits the lifespan will trip". A unit test prevents regression. Recommendation: **yes**, add a single-line test in `tests/test_graph/test_neo4j.py` that calls `close()` twice and asserts no raise.

**C3. Should `Neo4jRepository.close` be exposed as a context manager (`__enter__/__exit__`) for symmetry with `MemoryService` patterns?**
*Why it matters*: marginal value. Recommendation: **no**, YAGNI — only the lifespan calls it, and the lifespan already manages it.

---

## D. `.env.example` content (FR-004 / H1 + L3)

**D1. Current `.env.example` (HEAD) does not contain the "use: memento-password" hint flagged in H1. Was this fixed in flight, or is feedback.md describing an older revision?**
*Why it matters*: if it's already gone, FR-004 is partly satisfied and the spec should record that. If it's still on the original `feature/container-setup` branch but already merged-and-cleaned on `main`, the spec needs to reflect what's actually in `main`. Action: **verify and update spec wording to "ensure no shared default password hint is present" rather than "remove it"**.

**D2. Do you want `.env.example` to gain a generation hint (e.g., `# e.g. openssl rand -base64 12`)?**
*Why it matters*: H1 calls it optional; spec FR-004 calls it permitted. Decide whether it ships.

| Option | Description |
|--------|-------------|
| A (Recommended) | Yes — add `# Generate one with: openssl rand -base64 12`. Helpful, no cred drift risk. |
| B | No — keep it minimal; users who don't know how to generate a password should learn. |

*Recommendation*: **A** — friction reduction with no security cost.

**D3. L3 (sectioning `.env.example` so power users know which vars compose ignores). In scope or deferred?**
*Why it matters*: this is a real source of confusion. Spec doesn't mention L3 explicitly.

| Option | Description |
|--------|-------------|
| A (Recommended) | In scope — add a `# Dev-only — ignored by docker-compose` header above the dev-only block. ~30s of work, big readability win. |
| B | Deferred to known-tech-debt.md with rationale "two-file split is heavier and not yet justified". |
| C | NA — recorded in Assumptions with rationale. |

*Recommendation*: **A** — exactly the kind of free polish this spec is for.

**D4. Should `MEMENTO_MAX_MEMORY_LENGTH` (currently in `.env.example` line 13) stay there, or move out?**
*Why it matters*: it's also ignored by compose. Same call as D3.

**D5. Should the spec require a verification step that `docker compose config` parses with the new `.env.example` after a fresh `cp` and password fill-in?**
*Why it matters*: this is a one-second test; T015 in 002 was unchecked (M1). Recommendation: **yes**, fold into FR-007's verification list.

---

## E. Bootstrap callout (FR-005 / H2)

**E1. As of "today" (2026-05-06 per spec date), what's the actual state of the publish bootstrap?** Has `v0.0.2` been built and pushed to GHCR? Is the package set to Public? `git log --oneline` shows `faf148e 002-container-setup: setup containers` merged but no tag visible — has `auto-tag.yml` actually fired against `main` yet?
*Why it matters*: FR-005 has a conditional that depends on this answer. If the bootstrap is closed today, FR-005 is satisfied by removing the callout requirement; if open, the callout must ship. Either way the spec should not leave this in superposition.

**E2. If the bootstrap is currently open, do you want the callout removed in this spec's final commit (assuming bootstrap closes during the work), or do you want to ship the callout regardless and remove it in a follow-up?**

**E3. Concrete callout wording. Use the H2 suggestion verbatim, or tweak?**
*Suggested*:
> **First-publish bootstrap**: until the first `vX.Y.Z` image has been built and the GHCR package visibility is set to Public, `docker compose pull` returns `manifest unknown`. Track first-publish status at <https://github.com/rigrergl/memento/pkgs/container/memento>.

Recommendation: ship verbatim.

**E4. Where exactly in the README does the callout go?**
*Why it matters*: "Power-User Setup" is named in feedback; spec doesn't pin the heading. Recommendation: **immediately under the `## Power-User Setup` heading, before the install commands**.

**E5. Should the callout also explain the workaround (build locally with `docker compose build`)?**
*Why it matters*: blocking error with no escape hatch is a frustrating first impression. But adding a build path conflicts with the "no `build:` in compose" decision in 002. Recommendation: **no** — directive: "wait for first publish or follow Developer Setup instead". Cleaner.

---

## F. Image filesystem permissions (FR-006 / H3)

**F1. `--chown=` on every `COPY`, or trailing `chown -R`?**

| Option | Description |
|--------|-------------|
| A (Recommended) | `COPY --chown=app:app --from=builder ...` on each COPY in the runtime stage. Layer-cache friendly, idiomatic. |
| B | Trailing `RUN chown -R app:app /app` after all COPYs. Simpler diff, breaks layer cache more aggressively. |

*Recommendation*: **A**, matches H3's explicit recommendation.

**F2. Do you want an explicit smoke test that the runtime user can write to the cache dir?**
*Why it matters*: H3 risk #1 (sentence-transformers writing lock files at first inference) is asymptomatic until first call. Recommendation: **yes**, fold into FR-007 verification list — `docker compose exec memento touch /app/.cache/models/.write-test && rm /app/.cache/models/.write-test`.

**F3. Should the user creation also receive a primary group?**
*Why it matters*: `useradd --system --create-home --uid 1001 app` without `--user-group` puts the user in the default group (often nogroup), which complicates `--chown=app:app`. Recommendation: **add `--user-group`** so `app:app` resolves cleanly.

**F4. Are there any other paths under `/app` (or elsewhere) that the runtime needs to write to that I'm missing?**
*Examples to check*: `/tmp` (already world-writable by OS), HuggingFace-specific dirs (`HF_HOME`, `TRANSFORMERS_CACHE`), `/app/.cache/huggingface` (set by sentence-transformers default). Confirm whether the sentence-transformers cache truly lands at `/app/.cache/models` (per `Config.embedding_cache_dir`) or whether the lib also probes `~/.cache/huggingface`.

---

## G. Power-user verification (FR-007 / M1)

**G1. SC-001 says "60 seconds excluding image pull". On what hardware are you benchmarking this?**
*Why it matters*: 60s is plausible on Linux native + SSD; on macOS Docker Desktop with VirtioFS it can stretch past that on cold caches. Recommendation: **specify "60s on the maintainer's local Linux VM with image already pulled"** as the reference target; document as Assumption.

**G2. T015 (`docker compose config` parses), T027 (`docker build` succeeds), T028 (multi-arch buildx), T029 (offline embedding), T030 (`curl` present in runtime), T031 (non-root). Which of these must this spec re-run?**
*Why it matters*: M1 lists them all unchecked. The spec FR-007 implicitly covers T032/T033 but doesn't enumerate the others.

| Option | Description |
|--------|-------------|
| A (Recommended) | All of T015 + T027–T031 are in scope, run against locally-built image. T028 (multi-arch) is gated on bootstrap because it's a publish-time step. |
| B | Only T015 + T032/T033; the rest are deferred. |
| C | All of T015 + T027–T033 (including multi-arch) — locally-built means using `docker buildx` to verify `linux/arm64` builds cleanly, even if not pushed. |

*Recommendation*: **C**. Buildx for arm64 under QEMU locally answers M5 too.

**G3. Where should FR-007's verification result be recorded?**
*Why it matters*: spec says "PR description (or commit messages) before this spec is considered complete" — too loose.

| Option | Description |
|--------|-------------|
| A (Recommended) | In `specs/003-container-polish-devloop/verification.md`, committed alongside the spec, listing each step with timestamp and observed output excerpt. Replays well, lives with the spec. |
| B | Only in PR description. Easier, but not searchable post-merge. |
| C | Both — committed `verification.md` summarized in PR description. |

*Recommendation*: **A** (or C if you want the PR description to also have the summary).

**G4. Does FR-007 require verification against the published image once the bootstrap closes, even if that means re-opening the spec?**
*Why it matters*: spec assumption says "rerun once the published image lands" but does not say who tracks it. Recommendation: **add a tracking note to `Documentation/known-tech-debt.md`** so it's not forgotten.

---

## H. Dev-loop validation (FR-008 / US2)

**H1. Which MCP client is the canonical client for the dev-loop validation?**
*Why it matters*: Claude Code, Gemini CLI, and Cursor all have different `.mcp.json` semantics; some perform `${VAR}` substitution, others don't (ADR-007 calls this out).

| Option | Description |
|--------|-------------|
| A (Recommended) | Claude Code, because it's named explicitly in ADR-007 as the target for `.mcp.json`-based dev. |
| B | Gemini CLI, because the maintainer also uses it (per `feature/spec-kit-merge-gemini-claude` history). |
| C | Both — validated against both, recorded in verification.md. |

*Recommendation*: **C** if both are routinely used, else **A**.

**H2. The `.mcp.json` `${VAR}` substitution requires the env vars exported in the launching shell. Where do you want to document the launching ritual?**
*Why it matters*: a user who runs `claude` in a fresh shell without `direnv` will see `mcp-neo4j-cypher` fail to authenticate, with an obscure error.

| Option | Description |
|--------|-------------|
| A (Recommended) | A "Developer Setup" subsection in README explicitly listing `set -a; source .env; set +a` (or `direnv allow`) before launching the MCP client. |
| B | A `Makefile` target like `make dev` that does it. |
| C | A README note pointing at `direnv` only. |

*Recommendation*: **A** + **C** (mention direnv as the recommended pro option).

**H3. Should the dev loop test require `mcp-neo4j-cypher` at a pinned version?**
*Why it matters*: `uvx mcp-neo4j-cypher` fetches latest by default. Pinning protects the dev loop from upstream breakage. Recommendation: **yes**, pin in `.mcp.json` (`uvx mcp-neo4j-cypher@<version>`), record the pin choice in research.

**H4. SC-003 says "new description on next tool listing within 5 seconds of save". What measurement protocol satisfies SC-003?**
*Why it matters*: 5s is a tight threshold; varies by host load.

| Option | Description |
|--------|-------------|
| A (Recommended) | Manual: edit description, save, immediately invoke `recall` from the MCP client; record observation that within ≤2 round-trips the new description is reflected. Loosen "within 5 seconds" to "on the next round-trip after worker respawn". |
| B | Scripted: a small test script that watches `--reload` output and times it. Heavier; questionable value. |

*Recommendation*: **A**, and **soften SC-003 wording** to "on the next round-trip after `--reload` triggers" since it's the meaningful behavior; the wall-clock 5s is a proxy.

**H5. SC-003 references "5 seconds of save"; the spec's edge case says some clients only refresh on reconnect. Should SC-003 be rewritten to acknowledge the client-cache caveat from the edge case?**
*Why it matters*: as written, SC-003 is conditionally false (e.g., for Claude Desktop). Recommendation: **yes**, rewrite as "on the next tool listing or call following the worker respawn".

**H6. The dev loop's `remember`/`recall` validation goes through `mcp-neo4j-cypher` — what specific Cypher query are you considering canonical?**
*Suggested*:
```cypher
MATCH (m:Memory) WHERE m.content CONTAINS $needle RETURN m.id, m.content, m.confidence, m.created_at LIMIT 5
```
*Why it matters*: the spec mentions "direct Cypher query" without prescribing one; the verification record will need a canonical query so a reader can repro. Recommendation: ship the above as the canonical "DB-state probe" in `verification.md`.

**H7. Should the dev-loop validation also verify that vector search through Cypher returns the same memory as `recall`?**
*Why it matters*: this would prove the vector index is functional, not just node insertion. Pulls in `db.index.vector.queryNodes(...)` against the Memento embedding via `mcp-neo4j-cypher`. Adds value but adds setup. Recommendation: **yes** — exactly the proof that the dev loop is end-to-end. Record in `verification.md`.

---

## I. Feedback ledger triage (FR-009 / FR-010)

For each feedback item from `specs/002-container-setup/feedback.md`, decide its terminal state. The spec demands one of: **Resolved** (fixed in this spec), **Deferred** (added to `known-tech-debt.md`), or **NA** (recorded in this spec's Assumptions). I've pre-filled my recommendations; please confirm or override each.

| ID | Item | My recommendation | Confirm |
|----|------|-------------------|---------|
| C1 | Healthcheck shape | Resolved (FR-001) | ? |
| C2 | Lifespan resource leak | Resolved (FR-002) | ? |
| H1 | `.env.example` shared password hint | Resolved (FR-004) | ? |
| H2 | README bootstrap callout | Resolved (FR-005) — may become NA if bootstrap closes mid-spec | ? |
| H3 | `chown` not recursive | Resolved (FR-006) | ? |
| H4 | `Neo4jRepository.close` not idempotent | Resolved (FR-003) | ? |
| M1 | T015/T027–T034 unchecked | Resolved (subsumed in FR-007) | ? |
| M2 | `embedder` lacks type hint | Resolved (FR-012) | ? |
| M3 | `_get_tool_fn` event-loop-per-call | Deferred to known-tech-debt.md (test-only, no user impact) | ? |
| M4 | AGENTS.md hardcodes spec path | Resolved (FR-011) | ? |
| M5 | Multi-arch QEMU build untested | Resolved-ish: cover by local `docker buildx build --platform linux/arm64` smoke test in this spec; remaining publish-time risk → known-tech-debt | ? |
| M6 | `auto-tag.yml` TOCTOU | NA per spec assumption (low cadence) — add explanatory comment to workflow | ? |
| L1 | `patch("asyncio.to_thread")` global form | Deferred to known-tech-debt | ? |
| L2 | `Dockerfile` copies `pyproject.toml` unnecessarily | Investigate-then-decide (if unused, drop in this spec; trivial) | ? |
| L3 | `.env.example` lists ignored vars | Resolved (see D3) | ? |
| L4 | Cache-dir contract implicit | Resolved (one-line cross-reference comment) | ? |
| L5 | ADR-007 `v0.2.0` vs compose `v0.0.2` | Resolved (one-line ADR fix) | ? |
| L6 | Two import styles in test file | Deferred to known-tech-debt | ? |
| L7 | `embedder` global never read | Investigate-then-decide (likely keep for symmetry with FR-012's "all four placeholders" wording) | ? |

**I1. Confirm or override each row above.** If overriding, a one-line rationale is enough.

**I2. Does this spec own writing the `Documentation/known-tech-debt.md` entries for the deferred items, or do you want a follow-up "tech-debt sweep" PR?**
*Recommendation*: **own them in this spec** — it's exactly what FR-009/FR-010 require to be done at ship time.

**I3. For each Deferred item, the existing tech-debt entries (TD-001..TD-004) include severity, status, affected locations, and remediation. Do you want new entries to follow that template strictly, or a lighter "Sweep entry" style for batch-deferred items?**
*Recommendation*: **strict template** — they're more useful that way and the cost is small.

**I4. NA items go into `Assumptions`. Today the Assumptions section has 6 bullets. Should NA-recording be a fresh subsection (e.g., `## Assumptions / Not-Applicable Items`) or interleaved with the existing assumptions?**
*Recommendation*: **fresh subsection `### Feedback Items Recorded as Not-Applicable`** with one bullet per item.

---

## J. AGENTS.md hardcoded path (FR-011 / M4)

**J1. Replacement strategy for the hardcoded `specs/002-container-setup/plan.md` reference?**

| Option | Description |
|--------|-------------|
| A (Recommended) | Read `.specify/feature.json`'s `feature_directory` and link `<feature_directory>/plan.md`. Requires the AGENTS.md reader to chase the JSON, but agents can. |
| B | Generic "the most recent plan under `specs/`". Cheaper but vague. |
| C | A small script (`.specify/scripts/bash/current-plan.sh`) that prints the current plan path; AGENTS.md instructs the agent to invoke it. |

*Recommendation*: **A** — ships today, agents already read JSON, no new script.

**J2. Should `CLAUDE.md` and `GEMINI.md` (currently `@AGENTS.md` symlinks per CLAUDE.md content) be left alone, or also rewritten?**
*Recommendation*: **left alone** — they delegate to AGENTS.md, fix flows through.

**J3. Should the spec require an automated check (e.g., a pre-commit hook or CI step) that AGENTS.md does not regress to a hardcoded path?**
*Recommendation*: **no, YAGNI** — the test is "does AGENTS.md mention `specs/<digits>-...`", and one regression every two specs is cheaper than the hook.

---

## K. Embedder annotation + global hygiene (FR-012 / M2 / L7)

**K1. The fix is `embedder: IEmbeddingProvider | None = None`. Confirm `IEmbeddingProvider` is the right annotation (vs the concrete implementing class).**
*Recommendation*: **interface** — matches "Interface Segregation" pattern in AGENTS.md.

**K2. L7 says `embedder` global is never read after lifespan populates it. Keep it as a placeholder for future tests, drop it, or convert to a local in `lifespan`?**

| Option | Description |
|--------|-------------|
| A (Recommended) | Keep + annotate (per FR-012). YAGNI cuts both ways: removing today and re-adding next month is churn. The placeholder is two lines. |
| B | Convert to a local in `lifespan`. Drop FR-012's "all four placeholders" wording to "all three". Slightly purer YAGNI. |
| C | Drop entirely. |

*Recommendation*: **A** — minimal, FR-012 is already written for it.

**K3. Should the spec also require type-checker validation (mypy/pyright) on the changed file, or is "code reviewer eyeballs" enough?**
*Recommendation*: **eyeballs** — repo doesn't run a type checker today; introducing one is out of scope.

---

## L. Dev-loop contract change (FR-013 / US2.4)

**L1. Which tool gets the description enrichment, and what's the new wording?**
*Why it matters*: this is the "small contract change" the dev loop validates against. The spec calls it "purely additive, has zero behavioral risk", but the wording matters because it lands on `main` permanently.

Suggested options:

| Option | Tool | Suggested addition |
|--------|------|-------------------|
| A (Recommended) | `recall` | "Results are ordered by descending vector-similarity score; `limit` caps the result count (default 10, hard max enforced by the vector index size)." |
| B | `remember` | "`confidence` is a float in [0.0, 1.0]; values outside the range are rejected. Stored memories are immutable from this tool — there is no `update`/`delete` companion." |
| C | Both — two-tool change is still a single PR. |
| D | Different tool / wording — supply yours. |

*Recommendation*: **A** — `recall`'s ordering and limit are the most actually-useful piece of behavioral truth a caller needs. C is also fine if you want the spec's "real improvement" criterion to be unambiguous.

**L2. Should the description say anything about embedding-model identity (e.g., "Vectors are produced by the configured local sentence-transformers model")?**
*Recommendation*: **no** — couples the docstring to a config value that may change.

**L3. The contract change is a docstring; the MCP tool registration uses the docstring as the tool description. Should there also be a corresponding update to `specs/001-baseline-rag/contracts/recall-tool.md` (or wherever the canonical contract lives)?**
*Why it matters*: contract drift between docstring and contract file. Recommendation: **yes**, mirror the addition into the contract file.

**L4. Do you want a test that asserts the new docstring is present in the registered tool's metadata (so a future refactor can't silently strip it)?**
*Recommendation*: **no** — over-rotating; docstrings are visible in code review.

---

## M. Test code drift (M3 / L1 / L6)

**M1. M3 (`_get_tool_fn` does `asyncio.run` per call). Defer or fix?**

| Option | Description |
|--------|-------------|
| A | Fix in this spec — fixture-based or pytest-asyncio. |
| B (Recommended) | Defer to known-tech-debt with rationale "tests run fast today; refactor when we have a concrete pain point". |

*Recommendation*: **B**, classic YAGNI.

**M2. L1 (asyncio.to_thread patch path). Defer or fix?**
*Recommendation*: **defer** — purely stylistic; no behavior change.

**M3. L6 (two import styles in test file). Defer or fix?**
*Recommendation*: **fix** if you're already touching the test file, **defer** otherwise. Predict: probably touching it for `embedder` annotation tests, so **fix**.

---

## N. Documentation drift (L2 / L4 / L5)

**N1. L2 — Dockerfile copies `pyproject.toml` into runtime stage. Verify whether `fastmcp run`'s startup actually reads it. If not, drop the COPY in this spec?**
*Recommendation*: **verify and drop if unused**. The verification is `docker run --rm <image> sh -c 'ls -la /app/pyproject.toml'` followed by attempting a tool call after `mv pyproject.toml pyproject.toml.bak` — if the server still serves, drop the COPY.

**N2. L4 — Cache-dir cross-reference comment. Where does the comment go?**

| Option | Description |
|--------|-------------|
| A (Recommended) | A comment in the `Dockerfile` near the model bake step pointing at `Config.embedding_cache_dir`'s default in `src/utils/config.py`. |
| B | A comment in `src/utils/config.py` near the default pointing at the Dockerfile. |
| C | Both. |

*Recommendation*: **A** — Dockerfile is more likely to drift, so the warning belongs there.

**N3. L5 — ADR-007 says `v0.2.0` while compose says `v0.0.2`. Spec doesn't explicitly mention this; is it in scope?**
*Recommendation*: **in scope** — single-line fix, exactly the kind of hygiene this spec exists for. The example in ADR should be updated to `v0.0.2` (or to a generic `v<X.Y.Z>` placeholder, which doesn't drift).

**N4. Should the README also be aligned with whatever pinned tag is current at ship time?**
*Recommendation*: **yes** — fold into FR-007 verification.

---

## O. Future-only risks (M5 / M6)

**O1. M5 — multi-arch QEMU build perf. Spec assumption mentions it as a "known unknown". Want to also do a one-time local `docker buildx build --platform linux/arm64` to confirm it at least *completes*?**
*Recommendation*: **yes** — ~10 minutes locally, big risk reduction for first publish.

**O2. M6 — `auto-tag.yml` TOCTOU on concurrent merges. Comment-only fix?**
*Recommendation*: **yes**, single comment in the workflow YAML noting the assumption of low cadence and how to recover (re-run failed publish).

**O3. Should the spec specify the comment's wording, or leave it to the implementer?**
*Recommendation*: **specify** to avoid bikeshedding:
```yaml
# NOTE: this workflow assumes low (single-digit / month) release cadence.
# Two PRs landing on main in quick succession can both pass the "tag exists?"
# check before either pushes; the second push will fail loudly. Re-run the
# failed workflow once the first tag is published.
```

---

## P. Spec scope and shipping

**P1. US3 (hygiene cleanup) is P3 but contains FR-011 and FR-012, which appear to also be required for FR-009/FR-010 (M2 and M4 closure). Is the priority labeling consistent?**
*Why it matters*: P3 reads as "deferrable", but FR-009 says all High-and-above feedback items must be Resolved or Deferred-with-rationale. M2 and M4 are Mediums, so FR-010 binds them. If P3 means "deferrable", then FR-010 NA-with-rationale is the path; if P3 means "this spec polishes them", then it's consistent.
*Recommendation*: **either renumber US3 to P2, or add a sentence clarifying that P3 here means "low risk if shipped slipped within this spec, not deferrable to a future spec"**.

**P2. Should US1, US2, US3 each become its own PR (incremental delivery), or one PR for all?**

| Option | Description |
|--------|-------------|
| A | Three PRs in order: polish (US1) → hygiene (US3) → dev-loop validation (US2). Each is independently mergeable per the Independent Test on each user story. |
| B (Recommended) | One PR. The spec is small; review burden is lower than the three-PR coordination cost; the dev-loop validation in US2 actually *exercises* the US1 fixes. |
| C | Two PRs: US1 + US3 (polish), then US2 (validation that depends on the polish). |

*Recommendation*: **B** — but if you have a strong "small PRs" preference, **C** is the natural split.

**P3. The spec is dated 2026-05-06, status Draft. What's the target ship window?**
*Why it matters*: SC-001's "60s" and the timing in FR-007 imply benchmarking on whatever hardware you have at ship time.

**P4. Are there any feedback items not in `feedback.md` (e.g., chat/Slack/email comments) you want in this spec's scope but didn't make it into the ledger?**
*Recommendation*: ship them as additional FRs now; cheaper than a 004 spec.

**P5. Out-of-scope statement: should the spec explicitly call out things it is NOT doing?**
*Examples*: Cloud Run deployment (deferred to a future spec), TD-001 logging fix, TD-002 vector-index migration, TD-004 longer-term distribution decision, the M3/L1/L6 test refactors.
*Recommendation*: **add a `## Out of Scope` section** — costs nothing, prevents reviewer confusion.

---

## Q. Verification recording and reproducibility

**Q1. SC-007 says "completes in under 5 minutes for someone following the README's Developer Setup". The "someone" is who, exactly?**

| Option | Description |
|--------|-------------|
| A | The maintainer (you), running through it once at ship time. |
| B (Recommended) | A teammate / fresh-eyes reviewer who has not seen the spec, on a Linux VM matching the dev VM's spec. |
| C | A fresh AI agent. The whole point of the dev loop is agent autonomy; "someone" being an agent matches the user-story phrasing of US2. |

*Recommendation*: **C** — it's the explicit motivation in ADR-007. If C is chosen, the verification log should be the agent's transcript or a summary of it.

**Q2. Should `verification.md` (per G3) include a section that re-runs verification post-bootstrap (against the published image)?**
*Recommendation*: **yes**, appended after first publish, not gating the merge.

**Q3. Should the spec require that all SC values (60s, 5s, 5 min) be measured-and-recorded, not just observed-as-feeling-OK?**
*Recommendation*: **yes** — record actual numbers in verification.md, even if approximate.

---

## R. Things I noticed that the spec doesn't mention

**R1. `Neo4jRepository` constructor signature: `Neo4jRepository(uri=..., user=..., password=...)`. Does the spec want to verify there's no other resource-allocation pre-`try` (e.g., embedding model load happening before the try)? Today the order is `Config()` → embedder → `Neo4jRepository(...)`, and embedder load can be slow but does not allocate "leakable" resources. Worth a one-line note in the lifespan saying "embedder construction is reentrant and resource-free; Neo4jRepository owns the only leakable handle"?**
*Recommendation*: **no, comment-as-spec is overkill**, but the invariant could go in `contracts/server-lifespan.md` if updated.

**R2. The `--reload` watcher restarts on changes under the file FastMCP is running. Does it also see changes in imported modules (`src/memory/*`, `src/graph/*`)?**
*Why it matters*: if not, an agent editing `MemoryService` doesn't see their change reflected — the dev loop is partially broken. Recommendation: **verify as part of FR-008's exercise**, and if the watcher misses transitive imports, document the limitation in the README.

**R3. `mcp-neo4j-cypher` requires the Neo4j Bolt port to be reachable. The compose file binds Bolt to `127.0.0.1:7687`. Confirm the dev-loop client (running on the VM host) can reach `localhost:7687` — i.e., the VM has port-forwarding from the dev's interactive shell to the bolt port.**
*Recommendation*: confirm and note in README.

**R4. `Documentation/known-tech-debt.md` follows a format: severity, status, context, risk, affected locations, remediation. Some 002 feedback items don't have natural "remediation" because they're advisory only (e.g., M6 comment, L1 stylistic). Should the format admit a "Remediation: not applicable" sentinel, or should we widen the template?**
*Recommendation*: **allow "Remediation: N/A — advisory-only" as a sentinel** rather than widening the template.

**R5. The spec's date and currentDate context (`2026-05-06`) suggest this is happening today. Are there any time-sensitive dependencies (e.g., FastMCP version, neo4j driver version, sentence-transformers version) that should be re-checked online before this spec ships, per AGENTS.md's "always look up time-sensitive information"?**
*Recommendation*: **yes** — at ship time, re-verify FastMCP's `--reload` behavior and any new health-endpoint feature has not landed that would simplify A1.

**R6. The spec doesn't mention how to handle a stale `neo4j_data` volume from a previous run with a different password. A new user re-running with a fresh `.env` will hit `AuthenticationFailed` from Neo4j. Is this a documented FAQ item?**
*Why it matters*: extremely common first-run failure mode for `docker compose` setups using auth.
*Recommendation*: **add a FAQ/troubleshooting note** to the README ("If `docker compose up -d` reports an auth failure after changing the password, run `docker compose down -v` to wipe the Neo4j volume").

**R7. Per AGENTS.md's project-level guidance, the published Docker image runtime is `python:3.12-slim`, but the dev VM may run a different Python version. Does the spec require any version-floor verification before claiming dev-loop parity?**
*Recommendation*: **no, but document the minimum** in the README's Developer Setup ("Python 3.10+, matching `pyproject.toml`'s `requires-python`").

**R8. Spec's edge case mentions "MCP clients cache tool descriptions per session". Is there a known-good list of clients with which the validation has been (or will be) exercised?**
*Recommendation*: **yes**, list them in the verification record (e.g., "Claude Code 1.x: respawns subprocess; Gemini CLI 0.x: same; Cursor: untested").

---

## S. After the answers

Once these are answered, my plan is to:

1. Update `spec.md` per the answers — primarily the `## Clarifications / ### Session 2026-05-XX` block plus targeted edits in FRs and Assumptions.
2. Note any new decisions that belong in `Documentation/known-tech-debt.md` and the post-spec follow-up list.
3. If the changes materially shift scope (e.g., adding G2's T028 expansion or P5's Out of Scope), refresh `checklists/requirements.md` to reflect them.
4. Hand the spec back for `/speckit-plan`.

If you'd prefer to answer in batches (e.g., A–D first, then E–H), call out where you want me to stop and apply the partial answers before continuing.

---

## Answers — Session 2026-05-07

Recorded by clarifier on behalf of the maintainer. Where an answer materially changes the spec, the spec has been updated in the same session; this block is the source of truth for *why*.

> **Cross-cutting overrides**
> - **All performance/timing constraints are dropped from this spec.** "60s healthy", "5s reload reflection", "5min dev-loop round-trip" all came from the previous model's recommendation, not the maintainer. Future timing concerns will be handled in a follow-up spec only if they become a real pain point.
> - **`mcp-neo4j-cypher` is removed from the dev loop.** The DB-state probe will use the Neo4j CLI (`cypher-shell`) directly. `.mcp.json` should drop the `neo4j-cypher` server entry.

### A. Healthcheck redesign

- **Online research finding (A1)**: FastMCP itself does **not** ship a built-in healthcheck/liveness endpoint. The MCP protocol does not define one either — health checks are deployment-layer concerns, not protocol-layer. The canonical community pattern is to register a small `@custom_route` handler in FastMCP that returns HTTP 200 at `/health` (e.g., the pattern documented at <https://gofastmcp.com/servers/server> and the MCPcat health-endpoint guide). FastMCP issue #987 confirms there is no built-in. Plan-stage recommendation: add a `@custom_route("/health")` returning 200, switch the compose healthcheck to `curl -fsS http://localhost:8000/health`. Three lines of app code; no MCP protocol nuance in the curl invocation. (Option B from A1 — POST + initialize handshake — also works without app changes; left to plan stage to pick.)
- **A2 (status code)**: NA at clarifier stage; depends on A1's resolution at plan stage.
- **A3 (start_period / interval / timeout / retries)**: **Out of scope.** Whatever values are in compose today stay; if startup is too slow under any of them, that is a separate spec.
- **A4 (codify contract)**: keep contract implicit in `docker-compose.yml`. No separate `contracts/healthcheck.md`.
- **A5 (publish v0.0.3)**: **Yes**, ship `v0.0.3` as part of this spec's completion.
- **A6 (bundle bump or follow-up PR)**: **Bundle in the same PR** (see P below — single PR for the whole spec).

### B. Lifespan failure paths

> The maintainer reasonably asked: "do we have a leak today?" — **yes**, today's code has a real leak path. If `await asyncio.to_thread(repository.ensure_vector_index)` raises, the `try/finally` (which is *below* that line) never runs, so `repository.close()` is never called and the Neo4j driver's connection pool is leaked. The fix proposed in `specs/002-container-setup/feedback.md §C2` — open the `try` block immediately after `Neo4jRepository(...)` — is exactly right. We adopt it verbatim.

- **B1**: Option A — open `try` immediately after `Neo4jRepository(...)`. Document the construction-order invariant (embedder constructed before driver) in a one-line comment in `lifespan`.
- **B2**: Skip the additional unit test. Keeping it simple; the structural fix is obvious from the diff and the existing lifespan test suite already exercises the happy path.
- **B3**: Leave teardown error handling as-is (silent re-raise via `finally`). Logging is owned by TD-001.
- **B4**: No explicit `KeyboardInterrupt` / `CancelledError` handling — `try/finally` covers it.

### C. Idempotent close

> Maintainer's question: does the `with self._driver.session() as session:` pattern make `close()` idempotency moot? **No, but it's a fair confusion.** The `with` block scopes a *session* (one connection from the pool); `__exit__` closes that session correctly every time. The *driver* (`self._driver`) holds the connection pool itself and lives for the entire `Neo4jRepository` lifetime; calling `Neo4jRepository.close()` shuts the pool down. So `with` handles per-call sessions safely, but the driver must still be closed exactly once at lifespan teardown. H4 is about the driver close, not the sessions.
>
> The current Neo4j Python driver tolerates double-`close()`, so this is not a runtime bug today — it is a contract gap that *could* trip on a future driver upgrade or a test that re-enters the lifespan.

- **C1, C2, C3**: **Defer to `Documentation/known-tech-debt.md`** as low-priority tech debt. Not a real product issue today, and the maintainer is prioritizing shipping. New TD entry will note the trigger condition (driver upgrade or double-lifespan test) and the trivial remediation (add `_closed: bool` flag).

### D. `.env.example` content

- **D1**: Already fixed in flight on `main`. Current `.env.example` has no `memento-password` hint; just the 8-char minimum. **No further action.**
- **D2**: No generation hint added. Maintainer wants no further action on this file.
- **D3, D4 (L3 sectioning / `MEMENTO_MAX_MEMORY_LENGTH` placement)**: **Defer to tech debt** (see I-row L3). The "vars compose ignores" issue is real but low-priority; documenting it in tech debt is enough.
- **D5 (verification step)**: NA — no `.env.example` change in this spec, so no re-verification needed.

### E. Bootstrap callout

- **E1–E5**: **Bootstrap is closed.** Confirmed by clarifier: `git fetch --tags` resolves `v0.0.2` from `origin`, and the maintainer has confirmed GHCR visibility. FR-005 callout requirement is therefore **NA** — recorded in Assumptions, no README change. H2 in the feedback ledger flips to NA accordingly.

### F. Image filesystem permissions

- **F1**: Use **trailing `RUN chown -R app:app /app`** after all COPYs. Maintainer explicitly de-prioritised idiomatic / layer-cache concerns; the simple recursive chown is fine. (For context: "layer-cache friendly" means each `COPY --chown=` produces an independently cacheable layer; with a trailing `chown -R`, any change above invalidates that final ownership layer. This costs build time only — no security or correctness implication. Single-tenant container, single app user, no risk in granting `app` full ownership of `/app`.)
- **F2 (cache-dir write smoke test)**: Skip. Verification will exercise `remember`/`recall` end-to-end, which writes embeddings — that's evidence enough.
- **F3 (`--user-group` on `useradd`)**: **Yes** — so `app:app` resolves cleanly.
- **F4 (other paths)**: With recursive chown of `/app`, any path under `/app` is writable. `/tmp` is OS-default writable. HuggingFace defaults under `~/.cache/huggingface` would resolve under `/home/app` (also owned via `--create-home`). No additional paths to chown.

### G. Power-user verification

- **G1**: Hardware target deleted — **no benchmark target.** Maintainer dropped the 60s constraint entirely.
- **G2 (which T0xx tasks to re-run)**: Plan stage decides. Maintainer's directive: "do whatever you think is best to avoid issues in the future." Default at plan stage: T015 (`docker compose config`), T027 (`docker build`), T030 (`curl` present — note: only if A1 picks the curl-based shape), T031 (non-root) against locally-built image. T028 multi-arch defers to the high-priority tech debt (see O). T032/T033 already covered by FR-007/FR-008.
- **G3 (where verification is recorded)**: `specs/003-container-polish-devloop/verification.md`, committed alongside the spec. Summarised in the PR description.
- **G4 (re-run against published image)**: NA — bootstrap is closed; verification runs against the published `v0.0.3` once cut.

### H. Dev-loop validation

- **H1 (canonical client)**: **Both Claude Code and Gemini CLI.** The dev loop must be exercised against both. Recorded in the verification record.
- **H2 (env-var launching ritual)**: README "Developer Setup" subsection documents the launching ritual for both clients (e.g., `set -a; source .env; set +a` before launching, or `direnv` as the recommended pro option). NB: with `mcp-neo4j-cypher` removed, this only matters for `MEMENTO_NEO4J_PASSWORD` reaching the Memento server — the env-var-substitution-into-MCP-config concern goes away entirely.
- **H3 (pin `mcp-neo4j-cypher`)**: NA — `mcp-neo4j-cypher` is dropped from the dev loop and from `.mcp.json`. Use `cypher-shell` CLI instead.
- **H4, H5 (5-second SC-003)**: **Drop the 5-second wall-clock requirement.** SC-003 wording softens to "the new description is reflected on the next round-trip after the worker respawns." Acknowledges client-cache caveat from the edge case.
- **H6, H7 (canonical Cypher query, vector search verification)**: Yes, both. Document in `verification.md`. With `cypher-shell` as the probe tool, the canonical commands are something like:
  ```bash
  # Probe inserted memory
  docker compose exec neo4j cypher-shell -u neo4j -p "$MEMENTO_NEO4J_PASSWORD" \
    "MATCH (m:Memory) WHERE m.content CONTAINS 'needle' RETURN m.id, m.content, m.confidence LIMIT 5"

  # Probe vector index returns the same memory for a relevant query
  # (embedding generation is internal to Memento; this query confirms the index is functional)
  docker compose exec neo4j cypher-shell -u neo4j -p "$MEMENTO_NEO4J_PASSWORD" \
    "SHOW INDEXES YIELD name, type, state WHERE name = 'memory_embedding_index' RETURN *"
  ```
  Concrete final form left to plan stage.

**Testing instructions (to be added to `verification.md`)**: For each client (Claude Code, Gemini CLI), document:
1. Setup: `docker compose up neo4j -d`, env vars exported, `.mcp.json` honoured by client at repo root.
2. Prompt to give the agent (a short canonical prompt, e.g., "Add a sentence to `recall`'s description documenting that results are ordered by descending similarity score, then verify the change is visible by calling `recall` and confirm the description now contains the new sentence; then call `remember` with content 'clarification-test-needle' confidence 0.9, then call `recall` for 'clarification-test', then run a `cypher-shell` query to confirm the `Memory` node exists.").
3. Validation steps (clarifier, post-agent-run): inspect the agent's transcript for the `recall` call showing the new description; run the `cypher-shell` query directly against Neo4j to confirm the `Memory` node was created with the right content/confidence.

### I. Feedback ledger triage

| ID | Item | Terminal state | Notes |
|----|------|----------------|-------|
| C1 | Healthcheck shape | **Resolved** (FR-001) | A1 finalises shape at plan stage. |
| C2 | Lifespan resource leak | **Resolved** (FR-002) | Real leak; fix per B1. |
| H1 | `.env.example` shared password hint | **Resolved** (FR-004) | Already fixed in flight; FR-004 reads as "MUST remain free of shared password guidance" — non-regression posture. |
| H2 | README bootstrap callout | **NA** | Bootstrap is closed; recorded in Assumptions. |
| H3 | `chown` not recursive | **Resolved** (FR-006) | Trailing `chown -R` per F1. |
| H4 | `Neo4jRepository.close` not idempotent | **Deferred** | New low-priority TD entry. |
| M1 | T015/T027–T034 unchecked | **Resolved** | Subsumed in FR-007 verification record. |
| M2 | `embedder` lacks type hint | **Resolved** (FR-012) | But via "convert to local in lifespan" per K, not via adding global annotation. |
| M3 | `_get_tool_fn` event-loop-per-call | **Deferred** | Low-priority TD entry. |
| M4 | AGENTS.md hardcodes spec path | **Resolved** (FR-011) | Per J: read `.specify/feature.json`. |
| M5 | Multi-arch QEMU build perf untested | **Deferred — high priority** | Per O. |
| M6 | `auto-tag.yml` TOCTOU | **Deferred — high priority** | Per O. |
| L1 | `patch("asyncio.to_thread")` global form | **Deferred** | Low-priority TD entry. |
| L2 | Dockerfile copies `pyproject.toml` | **Deferred — low priority** | Per N. |
| L3 | `.env.example` lists ignored vars | **Deferred — low priority** | Per N. Names which vars: `MEMENTO_NEO4J_URI`, `MEMENTO_NEO4J_USER`, the `MEMENTO_EMBEDDING_*` block, `MEMENTO_MAX_MEMORY_LENGTH`. |
| L4 | Cache-dir contract implicit | **Deferred — low priority** | Per N. |
| L5 | ADR-007 `v0.2.0` vs compose `v0.0.2` | **Deferred — low priority** | Per N. |
| L6 | Two import styles in test file | **Deferred** | Low-priority TD entry. |
| L7 | `embedder` global never read | **Resolved** (FR-012) | Per K: convert to local in lifespan. |

- **I2 (own tech-debt entries here vs follow-up sweep)**: **Own them in this spec.**
- **I3 (template strictness)**: **Strict template** for new entries.
- **I4 (Assumptions NA placement)**: New `### Feedback Items Recorded as Not-Applicable` subsection under `## Assumptions`.

### J. AGENTS.md hardcoded path

- **J1**: Option A — read `.specify/feature.json`'s `feature_directory` and link `<feature_directory>/plan.md` (or have the agent discover it from there).
- **J2**: Leave `CLAUDE.md` / `GEMINI.md` alone — they delegate via `@AGENTS.md`.
- **J3**: No automated regression check.

### K. Embedder annotation + global hygiene

- **K1, K2**: **Option B** — convert `embedder` to a local variable inside `lifespan`. Only `service` is genuinely needed at module scope (so `patch.object(server_module, "service", ...)` keeps working in tests). YAGNI on globals that are never read elsewhere. FR-012 is updated accordingly.
- Open question for plan stage: `config` and `repository` are also currently module-level globals and may not need to be either; clarifier flagging but the maintainer's directive was specifically that "only memory service really needs it" — interpret as: convert all three (`config`, `embedder`, `repository`) to locals in `lifespan` and keep only `service` at module scope.
- **K3 (type-checker validation)**: No.

### L. Dev-loop contract change

- **L1, L2**: **Add parameter descriptions to both `remember` and `recall` tools.** The current FastMCP-decorated functions have no per-parameter docstring metadata — only top-level docstrings. Use `Documentation/legacy/mcp-tool-specification.md` for stylistic vibe (concise, parameter-focused, behavioral) but do not adopt the legacy file's verbose sample payload structure or its now-defunct `source` / `supersede_memory` features. Concretely:
  - `remember.content` — what the parameter is for, format expectation.
  - `remember.confidence` — float in [0.0, 1.0]; behavioural note about defaults/validation.
  - `recall.query` — natural-language search query.
  - `recall.limit` — result-count cap, default 10, ordering note.
  - The top-level docstrings can also gain a sentence each, time permitting.
  - Plan stage decides exact wording; FR-013 is updated to describe this scope.
- **L3 (mirror to canonical contract file)**: NA — no canonical contract file is being maintained for these tools right now (legacy spec is marked legacy). Skip.
- **L4 (assertion test on docstring presence)**: No.

### M. Test code drift

- **M1, M2, M3**: **Defer all of M3 / L1 / L6 to tech debt** (per the I table above).

### N. Documentation drift

- **All of L2 / L4 / L5 deferred to low-priority tech debt.** Maintainer's directive: rather than fix each one inline, batch them as low-priority debt entries.
- **`Documentation/known-tech-debt.md` format change**: add a **`Priority`** field (values `high` / `low` for now, expandable). Update existing TD-001..TD-004 to carry the new field. Document the field in a short header at the top of the file.

### O. Future-only risks

- **O1, O2**: **Defer M5 (multi-arch QEMU perf) and M6 (auto-tag TOCTOU) as high-priority tech debt.** Each gets its own TD entry. M5's TD entry should carry the recommendation "before next publish, run `docker buildx build --platform linux/arm64` locally to confirm completion within reasonable CI window"; M6's TD entry should record the comment-only mitigation suggested in O3 (or a structural fix when concurrent-merge cadence rises).

### P. Spec scope and shipping

- **P1 (US3 priority labelling)**: Resolves cleanly — US3's items either become Resolved (M2/M4 → FR-011/FR-012) or Deferred (the rest); nothing is silently dropped.
- **P2**: **One PR** for the whole spec.
- **P3 (target ship window)**: No timing target.
- **P4 (other feedback items)**: None additional.
- **P5 (Out of Scope section)**: Optional; not requested. Defer to plan stage if the planner wants one.

### Q. Verification recording and reproducibility

- **Q1**: **Option C — fresh AI agent.** This is the explicit motivation per ADR-007 and US2. The verification record is the agent's transcript or a summary thereof.
- **Q2 (post-bootstrap re-run)**: NA — bootstrap closed.
- **Q3 (record measured numbers)**: **No measurements required.** Drop wall-clock metrics from SCs.

### R. Things the spec doesn't mention

- **R1**: Skip the lifespan invariant comment; instead, record the "embedder is reentrant; driver owns the only leakable handle" invariant in the existing `specs/002-container-setup/contracts/server-lifespan.md` (one-line addition).
- **R2 (does `--reload` see transitive imports?)**: **In scope** — verify during FR-008 exercise. Document any limitation found in README.
- **R3 (Bolt port reachable from dev shell)**: **In scope** — confirm and note in README's Developer Setup.
- **R4 ("Remediation: N/A — advisory-only" sentinel)**: **Yes**, allow as a sentinel rather than widening the template.
- **R5 (re-verify time-sensitive deps before ship)**: **Yes**, plan stage should re-check FastMCP / neo4j-driver / sentence-transformers versions and any new health endpoint that may have shipped upstream.
- **R6 (FAQ for stale `neo4j_data` volume after password change)**: **Yes**, add a short troubleshooting note to README.
- **R7 (Python version floor)**: Document as "Python version must match `pyproject.toml`'s `requires-python`" in README's Developer Setup. Do **not** hardcode a specific version number anywhere; readers should check the relevant manifest files (`pyproject.toml`, `Dockerfile`'s `FROM python:`) for the current pinned versions.
- **R8 (clients tested for dev loop)**: Document in `verification.md` which clients have been exercised — at minimum Claude Code and Gemini CLI per H1; "Cursor: untested" is an acceptable sentinel.

### S. After the answers

- Clarifier scope ends at: (1) this answers section, (2) the in-place spec edits described above. **No `/speckit-plan` invocation.** Maintainer takes the spec from here.

