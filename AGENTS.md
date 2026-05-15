# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Project Overview

Memento is an MCP (Model Context Protocol) server that provides persistent memory capabilities for LLMs. It uses Python with FastMCP framework and Neo4j for graph-based vector storage, enabling semantic search and memory relationships.

## Architecture

The system follows a layered architecture:

- **MCP Server Layer**: FastMCP-based server exposing memory tools to LLM clients
- **Memory Service Layer**: Core business logic for memory operations (MemoryService)
- **Repository Layer**: Neo4j database operations (Neo4jRepository)
- **Provider Layer**: Pluggable embedding providers (local Sentence Transformers)

Key components:
- `MCPServer`: Main server entry point with tool registration
- `MemoryService`: Core memory operations with semantic search
- `Neo4jRepository`: Database abstraction for Neo4j operations
- `IEmbeddingProvider`: Interface for pluggable embedding providers
- `Factory`: Creates the configured embedding provider


## Prerequisites

Before running tests or starting the server, ensure:

- **Docker** is running (required for integration tests — Neo4j testcontainer starts automatically)
- **`uv`** is available in PATH
- Python dependencies are installed: `uv sync --all-groups`

## Development Commands

- `uv run python -m src.mcp.server` — start the MCP server
- `uv run pytest --cov=src --cov-report=term-missing` — run with coverage

## Testing

`uv run pytest` runs both unit and integration tests together. The Neo4j testcontainer starts automatically for integration tests and stops when the session ends.

To run integration tests only:

```bash
uv run pytest tests/integration/
```

**Important**: Integration tests are incompatible with `pytest-xdist` (`-n auto`). They share a single Neo4j testcontainer with per-test cleanup via an autouse fixture — parallel execution causes race conditions on the cleanup query. Always run integration tests sequentially.

**Pytest warnings must be fixed immediately.** Any time `uv run pytest` prints a "warnings summary" section, treat it as a failure to address before wrapping up the task — never ignore, defer, or hide it behind a global filter. Fix the warning at its source (update the deprecated API, bump the dependency, adjust the test). If the warning originates inside a third-party library we cannot patch, add a narrow filter in `pyproject.toml` under `[tool.pytest.ini_options].filterwarnings` that matches only the specific message and category, and leave a comment naming the library and the condition for removing the filter.

## Key Design Patterns

- **Factory Pattern**: For creating embedding providers
- **Repository Pattern**: For database operations abstraction
- **Interface Segregation**: Separate interfaces for each provider type
- **Plugin Architecture**: Swappable embedding providers

## Development Philosophy

Constitutional principles (YAGNI, KISS, TDD, layered architecture, and mandatory testing) are defined in `.specify/constitution.md`. Read it before making architectural decisions or reviewing plans.

**YAGNI (You Ain't Gonna Need It)**: Don't build features, methods, or abstractions until they're actually needed. If we don't have a concrete use case right now, don't implement it. This keeps the codebase lean and focused.

**KISS (Keep It Simple, Stupid)**: Always choose the simplest solution that works. Avoid over-engineering, premature optimization, and unnecessary complexity. Simple code is easier to understand, test, and maintain.

When reviewing architecture or planning tasks:
- Remove unused methods from interfaces
- Avoid building "might need later" features
- Choose simple implementations over clever ones
- Refactor to add complexity only when requirements demand it

## Working with Time-Sensitive Information

**IMPORTANT**: Always look up time-sensitive information online rather than relying on training data. Information that changes over time should be verified using web search or fetch tools.

**Always verify online:**
- Package versions (e.g., `pydantic-settings`, `sentence-transformers`)
- Framework APIs and breaking changes
- Best practices and current conventions
- Release dates and deprecation notices
- Security advisories and CVEs

**Example**: When adding a dependency, search PyPI for the latest version and release date rather than using potentially outdated training data.

## Versioning

**IMPORTANT**: Update the version in `pyproject.toml` whenever you make any functional change — new features, bug fixes, behavior changes, or dependency updates. Use [semantic versioning](https://semver.org/): patch for bug fixes, minor for new features, major for breaking changes.

Do not skip this step when wrapping up a task. If a PR or commit adds or changes behavior, the version must be bumped.

**Bump `pyproject.toml` and `docker-compose.yml` together.** The `image:` tag in `docker-compose.yml` pins `ghcr.io/rigrergl/memento:v<version>` and MUST match the new `pyproject.toml` version. The release flow is: version bump merges to `main` → `.github/workflows/auto-tag.yml` creates the `v<version>` git tag → `.github/workflows/publish.yml` builds and pushes the image. The compose pin needs to track the version that *will* be published.

Before opening a PR that bumps the version, grep the repo for the old version string and update every occurrence — `docker-compose.yml` is the one that's easy to miss.

## Integration Testing

`Documentation/test-instructions/` contains step-by-step instructions for running integration test suites manually or end-to-end. Each file describes a specific test scenario that requires a live environment (e.g., running Neo4j, loaded embeddings).

After making code changes, check this folder to see whether any of the test suites are relevant to what changed. If so, flag the applicable test instructions to the user and ask for permission before running them — do not run integration tests automatically.

## Specs Are Historical Context, Not Source of Truth

The `specs/` directory contains feature-by-feature spec/plan/research/tasks documents written *during* development of each change. Treat them as a **context playground** — a record of the rationale and trade-offs considered at the time, useful for understanding why a decision was made.

**Specs are not binding contracts after the fact.** Do not:
- Treat older FR numbers (e.g., "FR-012") as constraints on current work — the code may have legitimately moved past them.
- Retroactively edit historical specs to match current code. They are a snapshot, not a living document.
- Block a clean refactor because a previous spec required the thing you want to remove.

When current code conflicts with a spec: the code wins. The spec is the "why we did it that way at the time" — and that rationale is allowed to be revisited.

The single source of truth is the code itself, plus `AGENTS.md`, `Documentation/ADR/`, and the active in-flight spec (if any). Everything else under `specs/` is reference material.

## Nested Agent Instructions

This repo may contain `AGENTS.md` files in subdirectories. When you read or work within a subdirectory, check for an `AGENTS.md` file there and read it — it contains context and instructions specific to that directory. Subdirectory `AGENTS.md` files take precedence over this root file for anything within their scope.

## Documentation Structure

- `Documentation/GLOSSARY.md`: Shared vocabulary for the project (domain terms, user roles, deployment modes). Consult and extend this when introducing or disambiguating terminology.
- `Documentation/mcp-tool-specification.md`: Complete MCP tool API specifications
- `Documentation/detailed-architecture.md`: Class diagrams and detailed architecture
- `Documentation/data-model.md`: Memory data structure details
- `Documentation/sample-use-cases.md`: Example usage scenarios
- `Documentation/ADR/`: Architecture Decision Records
- `Documentation/strategic-planning/`: Exploratory ideas and research for future improvements (not committed to any roadmap). Read these for context on the direction the project may evolve, but do not treat them as active requirements.

## Active Technologies
- Python (see `pyproject.toml` for version constraints), FastMCP, Neo4j driver, sentence-transformers, Pydantic/pydantic-settings
- Neo4j (graph database with vector index capabilities)

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan.
The active implementation plan is at `specs/004-tier1-integration-tests/plan.md`.
<!-- SPECKIT END -->
