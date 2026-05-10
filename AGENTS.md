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


## Development Commands

- `uv run pytest` — run all tests
- `uv run pytest --cov=src --cov-report=term-missing` — run with coverage
- `uv run python -m src.mcp.server` — start the MCP server

## Key Design Patterns

- **Factory Pattern**: For creating embedding providers
- **Repository Pattern**: For database operations abstraction
- **Interface Segregation**: Separate interfaces for each provider type
- **Plugin Architecture**: Swappable embedding providers

## Development Philosophy

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

## Integration Testing

`Documentation/test-instructions/` contains step-by-step instructions for running integration test suites manually or end-to-end. Each file describes a specific test scenario that requires a live environment (e.g., running Neo4j, loaded embeddings).

After making code changes, check this folder to see whether any of the test suites are relevant to what changed. If so, flag the applicable test instructions to the user and ask for permission before running them — do not run integration tests automatically.

## Documentation Structure

- `Documentation/mcp-tool-specification.md`: Complete MCP tool API specifications
- `Documentation/detailed-architecture.md`: Class diagrams and detailed architecture
- `Documentation/data-model.md`: Memory data structure details
- `Documentation/sample-use-cases.md`: Example usage scenarios
- `Documentation/ADR/`: Architecture Decision Records

## Active Technologies
- Python (see `pyproject.toml` for version constraints), FastMCP, Neo4j driver, sentence-transformers, Pydantic/pydantic-settings
- Neo4j (graph database with vector index capabilities)

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan.
The current feature directory is defined in `.specify/feature.json` under
the `feature_directory` key. Read `<feature_directory>/plan.md` for the
active implementation plan.
<!-- SPECKIT END -->
