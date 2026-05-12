# Dev Loop Strategy

This document captures research and recommendations for evolving Memento's developer feedback loop — from the current state (pure unit tests + manual integration checklists) toward a layered, automated verification stack.

> Status: exploratory — nothing here is committed to. These are ideas to inform future planning.

---

## Current State

- **Unit tests** in `test_mcp/` use FastMCP `Client(server)` in-process against mocked Neo4j.
- **Unit tests** in `test_graph/` mock Neo4j at the repository layer.
- **Manual integration checklists** live in `Documentation/test-instructions/` and are run by a human (or with explicit permission) against a live stack.
- **Dev-loop MCP wiring**: ADR-007 registers both the Memento MCP and `neo4j-cypher` MCP in `.mcp.json`, giving a coding agent in YOLO mode a "call Memento → inspect Neo4j" self-validation loop during development.

The gap: there is no automated layer between pure unit tests and the manual checklists that exercises real Neo4j + real MCP protocol without human involvement.

---

## Option Analysis

### Option 1 — In-process FastMCP Client + Testcontainers (recommended primary layer)

Use the existing `async with Client(mcp_server) as client: await client.call_tool(...)` pattern from `test_mcp/`, but replace mocked Neo4j with a real container spun up by `testcontainers-neo4j`.

**How it works**: A `pytest` session-scoped fixture starts a Neo4j container once. Tests build the full `MemoryService + Neo4jRepository` stack against it, call tools through the FastMCP `Client`, then assert final DB state directly via Cypher queries through the driver.

**Pros**:
- Sub-second per test once the container is warm; full session startup is ~10–15 s
- Tests the real MCP protocol contract (same as a real client uses)
- Deterministic — normal breakpoints, no LLM variance
- Runs in CI and in Jules' VMs (Docker preinstalled)
- Lets tests assert exact node/edge/embedding state with Cypher
- This is the pattern FastMCP itself uses internally

**Cons**:
- Does not test the `fastmcp run --transport http` boundary
- Does not test transport-layer auth
- Does not validate whether an LLM picks the right tool from its description

**Fit**: Very strong. Covers ~95% of correctness bugs. This is the workhorse layer.

**Prerequisite**: The lifespan refactor from ADR-007 (moving `Service`/`Repository` construction out of module-import time and into the lifespan hook) is a prerequisite for clean test fixtures. These two pieces of work should be treated as one unit.

---

### Option 2 — Inspector CLI + Cypher CLI smoke scripts

Convert `Documentation/test-instructions/container-testing-instructions.md` into a shell script (~30 lines of bash) using `npx @modelcontextprotocol/inspector --cli` and `cypher-shell`. The script starts the stack, calls `tools/list`, calls `remember`/`recall`, then asserts via exit codes and `jq`.

**Pros**:
- Zero new Python deps
- Tests the actual `fastmcp run --transport http` server and Docker/port-binding config
- Headlessly runnable by any agent or CI job with a shell
- Cheap to add alongside existing manual documentation

**Cons**:
- Bash + `jq` is a poor language for multi-property assertions
- Snapshot-style assertions drift
- Multi-step flows get unwieldy fast

**Fit**: Good as a thin transport smoke layer on top of Option 1. Run on release, not every commit. Not a replacement for Python-level assertions.

---

### Option 3 — Subagent spawning (Claude Code Task tool)

Have the coding agent spawn a fresh general-purpose subagent whose role is "Memento user." The subagent has Memento MCP and `neo4j-cypher` MCP wired, makes tool calls in free-form scenarios, and reports a summary back to the parent agent.

**Pros**:
- The only option that tests LLM-driven tool selection
- Free-form scenarios (e.g., "remember three contradictory facts, then recall, check deduplication")
- Keeps verbose tool output out of the parent context window

**Cons**:
- Non-deterministic — LLM variance makes it a poor correctness oracle
- Real token cost per run (Sonnet/Opus-class subagents)
- Claude Code-specific; not portable to Jules or other agents
- Subagents cannot spawn their own subagents
- Worse than `pytest` for protocol/state correctness because an LLM sits between call and assertion

**Fit**: Narrow but irreplaceable. Use only to validate that tool descriptions and workflow guidance steer an LLM into the right call sequence. Not needed on every commit; needed when tool names, descriptions, or multi-step call dependencies change.

---

### Option 4 — Eval frameworks (mcp-eval / MCPJam / Arcade Evals / MCPLab)

Dedicated open-source frameworks for the "fake user → real LLM → your MCP server → assert tool calls + final state" pattern. `lastmile-ai/mcp-eval` is the most mature; it supports `Expect.tools.was_called("remember")`, sequence assertions, and LLM judges for qualitative checks. Cases can be auto-generated from tool schemas. CI-friendly with JSON/HTML reports.

**Pros**:
- The correct answer for validating LLM-tool interaction at scale
- Real metrics: TPR, FPR, tool-selection accuracy
- Bounded cost, reproducible runs with known LLM version
- Precedent: Neon moved tool-selection accuracy from 60% → 100% by tuning descriptions with Braintrust

**Cons**:
- New dependency and config surface to maintain
- API token cost per run
- Overkill until the tool surface area is stable

**Fit**: Introduce after the tool API stabilizes and tool ergonomics become the active focus. Gate behind a CI label so it doesn't run on every PR.

---

### Option 5 — Formalize the existing ADR-007 self-validation loop

The current `.mcp.json` wiring already gives a coding agent the "call Memento → query Neo4j → eyeball" loop. The lowest-cost improvement is to turn the eyeballing into a structured checklist the agent reads from `AGENTS.md`, so it isn't improvising verification each time.

**Pros**: Zero new infra. Works today. Same loop works in Jules' VMs.

**Cons**: The checklist is squishy — the agent decides what "good enough" means. No regression catching across PRs.

**Fit**: Keep as the baseline exploratory loop during active development. Layer 1 (Testcontainers) is what makes it stop being squishy.

---

## Recommended Layered Approach

These tiers are not mutually exclusive and are ordered by return on investment:

| Tier | What | When to run | Key benefit |
|------|------|-------------|-------------|
| 1 | `pytest` + FastMCP in-memory Client + `testcontainers-neo4j` | Every PR (skip by default in `uv run pytest`, require green before merge) | State correctness, schema validation, embedding integration |
| 2 | Inspector CLI + Cypher CLI shell smoke script | Release | Transport boundary, Docker/port-binding, env-var wiring |
| 3 | `mcp-eval` or equivalent eval suite | When tool surface stabilizes | LLM tool-selection accuracy, tool description ergonomics |
| 4 | ADR-007 dual-MCP exploratory loop | During active development | Fast exploratory feedback while building |

Build Tier 1 first. It captures the vast majority of correctness value and is the natural evolution of what already exists in `test_mcp/`.

---

## Key Gotcha: Module-Import Side Effects

The current `server.py` builds `Service`/`Repository` at module-import time. Tests that do `from src.mcp.server import service` bind to a `None` placeholder. The lifespan refactor in ADR-007 (moving construction into the lifespan hook) is a prerequisite for clean Tier 1 fixtures — treat them as one unit of work, not separate tasks.

---

## References

- `Documentation/ADR/ADR-007-*.md` — dual-MCP wiring and lifespan refactor context
- `Documentation/test-instructions/` — existing manual integration checklists
- `test_mcp/test_server.py` — current in-process FastMCP Client tests (mocked Neo4j)
- [testcontainers-python](https://testcontainers-python.readthedocs.io/) — container fixtures for pytest
- [lastmile-ai/mcp-eval](https://github.com/lastmile-ai/mcp-eval) — MCP eval framework reference
